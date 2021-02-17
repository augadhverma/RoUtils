from typing import Iterable
import discord

from datetime import datetime
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
        self.id = entry['_id']
        self.name = entry['name']

class TagPages(menus.ListPageSource):
    def __init__(self, entries, *, per_page=12):
        converted = []
        index = 1
        for entry in entries:
            name = f"{index}. {TagPageEntry(entry).name} (ID: {str(TagPageEntry(entry).id)[-1:-7:-1]})"
            converted.append(name)
            index+=1

        super().__init__(converted, per_page=per_page)

    async def format_page(self, menu, data):
        embed = discord.Embed(
            colour = discord.Colour.blurple(),
            description="\n".join(item for item in data)
        )

        return embed


class InfractionType(Enum):
    warn = 0
    tempmute = 1
    mute = 2
    kick = 3
    ban = 4
    unban = 5

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

class EmbedInfractionType(Enum):
    warn = "warned"
    tempmute = "tempmuted"
    mute = "muted"
    kick = "kicked"
    ban = "banned"
    unban = "unbanned"

    def __str__(self) -> str:
        return self.value

class EmbedLog:
    def __init__(self, ctx:commands.Context, embed:discord.Embed):
        self.ctx = ctx
        self.embed = embed

    async def post_log(self):
        channel = get(self.ctx.guild.text_channels, name="bot-logs")
        if channel:
            try:
                return await channel.send(embed=self.embed)
            except:
                return

class InfractionEntry:
    __slots__ = ("time", "reason","type","id")
    def __init__(self, ctx, entry:dict) -> None:
        self.ctx = ctx
        self.entry = entry
        self.time = f"* | Duration: {self.entry['time']}*" if self.entry['time'] else ""
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
                    name = f"#{entry['id']} | {InfractionType(entry['type']).name}",
                    value = f"**Moderator:** {await self.moderator(entry['moderator'])}\n**Reason:** {entry['reason']}\n**Offender:** {await self.moderator(entry['offender'])}"
                )
            except:
                pass

        return embed