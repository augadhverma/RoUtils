import discord

from datetime import datetime
from discord.ext import menus

class DiscordUser:
    def __init__(self, user:discord.User) -> None:
        self.user = user

class DiscordMember:
    def __init__(self, member:discord.Member) -> None:
        self.member = member

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