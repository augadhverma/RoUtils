"""
Represents various models.
Copyright (C) 2021  Augadh Verma

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

from __future__ import annotations

import datetime
import aiohttp
import discord
import humanize

from typing import Any, Optional, Union
from discord.ext import commands

from .bot import Bot
from .roblox import User, time_roblox

def utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)

def human_time(value, when=None) -> str:
    when = when or utcnow()
    return humanize.naturaltime(value, when=when)

def format_dt(dt: datetime.datetime, style=None):
    if style is None:
        return f'<t:{int(dt.timestamp())}>'
    return f'<t:{int(dt.timestamp())}:{style}>'

def format_date(dt) -> str:
    """Gives a relative and general timestamp.

    Parameters
    ----------
    dt : Union[datetime.datetime, None]
        The datetime to format into new timestamps.

    Returns
    -------
    str
        The timestamp to return.
    """
    if dt is None:
        return 'N/A'

    return f'{format_dt(dt, "F")} ({format_dt(dt, "R")})'

class HTTPException(Exception):
    def __init__(self, response, json):
        self.response = response
        self.status = response.status
        self.json = json

async def request(session: aiohttp.ClientSession, method: str,  url: str, *args, **kwargs) -> dict:
    r = await session.request(method, url, *args, **kwargs)
    json = await r.json()
    if r.status == 200:
        return json
    else:
        raise HTTPException(r, json)

class FakeUser(User):
    """Represents an unverified user with RoWifi."""
    def __init__(self, data: dict=None):
        if data:
            super().__init__(data)
        else:
            super().__init__({
                'name':'Unverified User',
                'id':0,
                'display_name':'Unverified User',
                'created_at':time_roblox(utcnow())
            })

class RoWifiUser(User):
    """Represents a verified user with RoWifi."""
    def __init__(self, data: dict, discord_id: int, guild_id: int = None) -> None:
        super().__init__(data)
        self.discord_id = discord_id
        self.guild_id = guild_id

    async def discord_user(self, ctx) -> discord.User:
        return await commands.UserConverter().convert(ctx, str(self.discord_id))

async def post_log(bot: Bot, guild: discord.Guild, **kwargs) -> Optional[discord.Message]:
    """Posts log in the set log channel.

    Parameters
    ----------
    bot : Bot
        The bot to access the database.
    guild : discord.Guild
        The guild to get the channel and post the log in.

    Returns
    -------
    Optional[discord.Message]
        The log posted.
    """
    settings = await bot.utils.find_one({'type':'settings'})
    if settings is None:
        return

    channel_id = settings.get('log')
    if channel_id:
        channel = guild.get_channel(channel_id)
        if channel is None:
            channel = await guild.fetch_channel(channel_id)
        
        if isinstance(channel, discord.TextChannel):
            return await channel.send(**kwargs)
    
    return

class TicketFlag(commands.FlagConverter, case_insensitive=True):
    user: Optional[Union[discord.Member, discord.User]]
    role: Optional[discord.Role]
    after: Optional[str]


class TagEntry:
    def __init__(self, document: dict[str, Any]):
        self.document = document

        self._id = document['_id']
        self.id = str(self._id)

        self.owner_id: int = document['owner']
        self.name: str = document['name']
        self.created: datetime.datetime = document['created']
        self.aliases: list[str] = document.get('aliases', [])

        self._embed: bool = document.get('embed', False)
        self._uses = document['uses']
        self._content: str = document.get('content', '')
        self._url: list[str, str] = document.get('url', [])
        self._image: str = document.get('image', None)

    @property
    def embed(self) -> bool:
        return self._embed

    @embed.setter
    def embed(self, value: bool):
        self._embed = value

    @property
    def uses(self) -> int:
        return self._uses

    @uses.setter
    def uses(self, value: int):
        self._uses = value

    @property
    def content(self) -> str:
        return self._content

    @content.setter
    def content(self, value: str):
        self._content = str(value) if value else '\uFEFF'

    @property
    def url(self) -> list[str, str]:
        return self._url

    @url.setter
    def url(self, value: list[str, str]):
        if value is not None and not value[1].startswith('http'):
            raise RuntimeError('Invalid URL was provided, please provide an URL that starts with http(s).')
        self._url = value

    @property
    def image(self) -> str:
        return self._image

    @image.setter
    def image(self, value: str):            
        if value is not None and not value.startswith('http'):
            raise RuntimeError('Invalid URL was provided, please provide an URL that starts with http(s).')
        self._image = value

    def to_send(self, *, timeout: Optional[float] = 180.0) -> list[str | discord.Embed, Optional[discord.ui.View]]:
        to_return = []
        if self.embed:
            embed = discord.Embed(
                colour = discord.Colour.blue(),
                timestamp = utcnow()
            )
            
            embed.set_footer(text=f'Tag: {self.name}')

            if self._content:
                embed.description = self._content

            if self._image:
                embed.set_image(url=self._image)
            
            to_return.append(embed)
        else:
            to_return.append(self._content)

        if self._url:
            view = discord.ui.View(timeout=timeout)
            button = discord.ui.Button(
                style = discord.ButtonStyle.link,
                label = self._url[0],
                url = self._url[1]
            )

            view.add_item(button)
            
            to_return.append(view)
        else:
            to_return.append(None)

        return to_return

    def to_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title = self.name,
            colour = discord.Colour.blue(),
            timestamp = utcnow()
        )

        embed.set_footer(text='Tag created at')

        embed.set_author(name=f'ID: {self.id}')

        embed.add_field(name='Owner', value=f'<@{self.owner_id}>')
        embed.add_field(name='Uses', value=f'{self.uses}')
        embed.add_field(name='Aliases', value=f'{len(self.aliases)}')

        return embed

    def to_dict(self) -> dict:
        result = {
            key[1:]: getattr(self, key)
            for key in self.__dict__.keys()
            if key[0] == '_' and hasattr(self, key)
        }

        del result['id']

        result['_id'] = self._id

        result['name'] = self.name

        result['owner'] = self.owner_id

        result['aliases'] = self.aliases

        result['created'] = self.created

        return result

class TagAlias(commands.FlagConverter, case_insensitive=True):
    _add: Optional[str] = commands.flag(name='add')
    remove: Optional[str]

class TagOptions(commands.FlagConverter, case_insensitive=True):
    content: Optional[commands.clean_content]
    url: Optional[str]
    image: Optional[str]
    embed: Optional[str] = commands.flag(default='false')
    