"""
Somewhat useful models
Copyright (C) 2021-present ItsArtemiz (Augadh Verma)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import datetime
import discord

from typing import TYPE_CHECKING, Union
from discord.ext import commands

from .models import CaseInsensitiveDict
from .context import Context


def roblox_time(time: str) -> datetime.datetime:
    try:
        return datetime.datetime.strptime(time, '%Y-%m-%dT%H:%M:%S.%fZ')
    except (ValueError, TypeError):
        return None

def time_roblox(time: datetime.datetime = None) -> str:
    time = time or datetime.datetime.now(datetime.timezone.utc)
    return datetime.datetime.strftime(time, '%Y-%m-%dT%H:%M:%S.%fZ')

class Object:
    __slots__ = ()
    id: int

class BaseUser(Object):
    __slots__ = (
        'name',
        'id',
        'display_name',
        'profile_url',
        'headshot_url',
        '_raw_data'
    )

    if TYPE_CHECKING:
        name: str
        id: int
        display_name: str
        profile_url: str
        headshot_url: str
        _raw_data: Union[CaseInsensitiveDict, dict]

    def __init__(self, data: dict) -> None:
        self._raw_data = CaseInsensitiveDict(data)

        self.name = self._raw_data['name']
        self.id = self._raw_data['id']
        self.display_name = self._raw_data['displayname']
        self.profile_url = f"https://www.roblox.com/users/{self.id}/profile"
        self.headshot_url = f"https://www.roblox.com/headshot-thumbnail/image?userId={self.id}&width=420&height=420"

class User(BaseUser):
    __slots__ = ('description', 'created_at', 'is_banned')

    if TYPE_CHECKING:
        description: str
        created_at: datetime.datetime
        is_banned: bool

    def __init__(self, data: dict) -> None:
        super().__init__(data)

        self.description = self._raw_data.get('description', '')
        self.created_at = roblox_time(self._raw_data['created'])
        self.is_banned = self._raw_data.get('isbanned', False)

class Role(Object):
    __slots__ = ('name', 'id', 'rank', 'membercount', '_raw_data')

    if TYPE_CHECKING:
        name: str
        id: int
        rank: int
        membercount: int | None

    def __init__(self, data: dict) -> None:
        self._raw_data = CaseInsensitiveDict(data)

        self.id = self._raw_data['id']
        self.name = self._raw_data['name']
        self.rank = self._raw_data['rank']
        self.membercount = self._raw_data.get('membercount')

class Member(BaseUser):
    __slots__ = ('group_id', 'role')

    if TYPE_CHECKING:
        group_id: int
        role: Role

    def __init__(self, data: dict, role: dict, group_id: int) -> None:
        super().__init__(data)

        self.group_id = group_id
        self.role = Role(role)

class RoWifiUser(Object):
    __slots__ = ('id', 'guild_id', 'roblox_user', 'discord_user', 'is_verified')
    
    if TYPE_CHECKING:
        id: int
        guild_id: int
        roblox_user: User | None
        discord_user: discord.User | None
        is_verified: bool

    def __init__(self, id: int, guild_id: int, is_verified: bool, roblox_user: User | None = None) -> None:
        self.id = id
        self.guild_id = guild_id
        self.roblox_user = roblox_user
        self.discord_user = None
        self.is_verified = is_verified

    async def fetch_discord_user(self, ctx: Context) -> discord.User:
        self.discord_user = await commands.UserConverter().convert(ctx, str(self.id))
        return self.discord_user