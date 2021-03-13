import discord
import re
import pytimeparse

from typing import Iterable, Optional
from datetime import date, datetime, timedelta
from discord.ext import menus, commands
from discord.utils import get
from enum import Enum

class DiscordUser(commands.Converter):
    async def convert(self, ctx, argument):
        return await commands.UserConverter().convert(ctx, argument)

class RobloxUser:
    def __init__(self, info:dict, discord_id:int) -> None:
        self.id = info['id']
        self.name = info['name']
        self.description = info['description']
        self.is_banned = info['isBanned']
        self.display_name = info['displayName']
        self.created = self.readable_time(info['created'])
        self.discord_id = discord_id

    def __repr__(self) -> str:
        return f"<User Id={self.id} name='{self.name}' description='{self.description}' is_banned={self.is_banned} display_name='{self.display_name}' created={self.created} discord_id={self.discord_id}>"

    def readable_time(self, roblox_time:str) -> datetime:
        return datetime.strptime(roblox_time, "%Y-%m-%dT%H:%M:%S.%fZ")

class TagPageEntry:
    __slots__ = ('id','name')
    def __init__(self, entry) -> None:
        self.id = entry['id']
        self.name = entry['name']

class TagPages(menus.ListPageSource):
    def __init__(self, entries, *, per_page=12):
        converted = []
        index = 1
        for entry in entries:
            name = f"{index}. {TagPageEntry(entry).name} (ID: {str(TagPageEntry(entry).id)})"
            converted.append(name)
            index+=1

        super().__init__(converted, per_page=per_page)

    async def format_page(self, menu, data):
        embed = discord.Embed(
            colour = discord.Colour.blurple(),
            description="\n".join(item for item in data)
        )

        return embed

class Paginator(menus.ListPageSource):
    def __init__(self, entries, *, per_page=12):
        super().__init__(
            entries, per_page
        )

    async def format_page(self, menu, page) -> discord.Embed:
        embed = discord.Embed(
            colour = discord.Color.blurple(),
            description='\n'.join(item for item in page)
        )
        return embed

class BanEntry:
    __slots__ = ("user","reason")
    def __init__(self, user:discord.User, reason:Optional[str]="No reason provided") -> None:
        self.user = user
        self.reason = reason
        

class BanList(menus.ListPageSource):
    def __init__(self, entries, *, per_page=12):
        converted = []
        for entry in entries:
            converted.append({'user':BanEntry(entry).user, 'reason':BanEntry(entry).reason})
        super().__init__(converted, per_page=per_page)

    async def format_page(self, menu, page) -> discord.Embed:
        embed = discord.Embed(
            timestamp = datetime.utcnow(),
            colour = discord.Color.blurple()
        )
        for ban in page:
            embed.add_field(
                
                name = f"{ban['user'].user}",
                value = ban['reason']
            )
        return embed

class InfractionType(Enum):
    warn = 0
    tempmute = 1
    mute = 2
    kick = 3
    ban = 4
    unban = 5
    autowarn = 6

    def __str__(self) -> str:
        return self.name

    def __int__(self) -> int:
        return self.value

class InfractionColour(Enum):
    warn = discord.Color.teal()
    tempmute = discord.Color.orange()
    mute = discord.Color.orange()
    kick = discord.Color.red()
    ban = discord.Color.dark_red()
    unban = discord.Color.green()
    autowarn = discord.Color.teal()

class EmbedInfractionType(Enum):
    warn = "warned"
    tempmute = "tempmuted"
    mute = "muted"
    kick = "kicked"
    ban = "banned"
    unban = "unbanned"
    autowarn = "warned (auto)"

    def __str__(self) -> str:
        return self.value

class EmbedLog:
    def __init__(self, ctx:commands.Context, embed:discord.Embed):
        self.ctx = ctx
        self.embed = embed

    async def post_log(self, channel:discord.TextChannel=None) -> discord.Message:
        channel = channel or get(self.ctx.guild.text_channels, name="bot-logs")
        if channel:
            try:
                return await channel.send(embed=self.embed)
            except:
                pass

class InfractionEntry:
    __slots__ = ("time", "reason","type","id")
    def __init__(self, ctx, entry:dict) -> None:
        self.ctx = ctx
        self.entry = entry
        self.time = f"* | Duration: {self.entry['expires']}*" if self.entry['expires'] else ""
        self.reason = f"{self.entry['reason']} + {self.time}"
        self.type = InfractionType[self.entry['type']].name
        self.id = self.entry['id']

    @property
    async def moderator(self) -> discord.User:
        return await DiscordUser().convert(self.ctx, str(self.entry['moderator']))

    @property
    async def offender(self) -> discord.User:
        return await DiscordUser().convert(self.ctx, str(self.entry['offender']))


class InfractionEmbed:
    def __init__(self, ctx, entries:Iterable):
        self.ctx = ctx
        self.entries = entries
    
    async def moderator(self, id:int) -> discord.User:
        return await DiscordUser().convert(self.ctx, str(id))

    async def embed_builder(self) -> discord.Embed:
        embed = discord.Embed(
            colour = discord.Color.blurple(),
            title = f"{len(self.entries)} Infractions Found"
        )
        for entry in self.entries:
            try:
                embed.add_field(
                    name = f"#{entry['id']} | {InfractionType(entry['type']).name} | {datetime.strftime(entry['added'],'%Y-%m-%d')}",
                    value = f"**Moderator:** {await self.moderator(entry['moderator'])}\n**Reason:** {entry['reason']}\n**Offender:** {await self.moderator(entry['offender'])}"
                )
            except:
                pass

        if len(self.entries) > 24:
            embed.description = f"Displaying {24}/{len(self.entries)} infractions."

        return embed

class DMInfractionEmbed(InfractionEmbed):
    def __init__(self, ctx, entries: Iterable):
        super().__init__(ctx, entries)

    async def embed_builder(self) -> discord.Embed:
        embed = discord.Embed(
            colour = discord.Color.blurple(),
            title = f"{len(self.entries)} Infractions Found"
        )
        for entry in self.entries:
            try:
                embed.add_field(
                    name = f"#{entry['id']} | {InfractionType(entry['type']).name} | {datetime.strftime(entry['added'],'%Y-%m-%d')}",
                    value = f"**Reason:** {entry['reason']}"
                )
            except:
                pass

        if len(self.entries) > 24:
            embed.description = f"Displaying {24}/{len(self.entries)} infractions."

        return embed

class UserInfractionEmbed:
    def __init__(self, type:InfractionType, reason:str, id:int):
        self.type = type
        self.embed_type = str(EmbedInfractionType[self.type.name])
        self.reason = reason
        self.id = id

    def embed(self) -> discord.Embed:
        embed = discord.Embed(
            title = f"You have been {self.embed_type} in RoWifi HQ. | Case Id: #{self.id}",
            colour = InfractionColour[self.type.name].value,
            description = f"**Reason:** {self.reason}",
            timestamp = datetime.utcnow()
        )

        if self.type == InfractionType.ban:
            embed.add_field(name="Appeal Form", value="https://forms.gle/5nPGXqiReY7SEHwv8")
            footer = "To appeal for your ban, please use the form above."
        else:
            footer = f"To appeal your {self.type}, please contact a staff member."
        embed.set_footer(text=footer)

        return embed

class UrlDetection:
    def convert(self, argument:str) -> bool:
        to_pass = (
            "https://rowifi.link",
            "https://patreon.com/rowifi",
            "https://tenor.com",
            "https://gyazo.com",
            "https://imgur.com",
        )
        found = []
        passed = []
        pattern = re.compile(
            r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
            )
        matches = pattern.findall(argument.lower())
        for match in matches:
            found.append(match)
            for a in to_pass:
                if a.replace("www.","") in match:
                    passed.append(a)

        if len(passed) == len(found):
            return True
        else:
            return False

    def invite_check(self, argument:str) -> bool:
        pattern = re.compile(r"(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?")
        matches = pattern.findall(argument.lower())

        if matches:
            return True
        else:
            return False