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
import enum
import aiohttp
import discord
import humanize

from typing import Any, Optional, Union, TypeVar
from discord.ext import commands
from bson import ObjectId

from .bot import Bot
from .roblox import User

Timestamp = TypeVar('Timestamp', float, int)

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
    if dt is None or not isinstance(dt, datetime.datetime):
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
                'displayName':'Unverified User',
                'created':'None'
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
            raise commands.BadArgument('Invalid URL was provided, please provide an URL that starts with http(s).')
        self._url = value

    @property
    def image(self) -> str:
        return self._image

    @image.setter
    def image(self, value: str):            
        if value is not None and not value.startswith('http'):
            raise commands.BadArgument('Invalid URL was provided, please provide an URL that starts with http(s).')
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
    extra: Optional[str] = commands.flag(default='false')

class InfractionType(enum.Enum):
    autowarn = 0
    automute = 1
    warn = 2
    mute = 3
    kick = 4
    softban = 5
    ban = 6
    unban = 7

    def __str__(self) -> str:
        return self.name

    def __int__(self) -> int:
        return self.value

    def __repr__(self) -> str:
        return f"<InfractionType name='{self.name}' value={self.value}>"

class InfractionColour(enum.Enum):
    autowarn = discord.Colour.teal()
    automute = discord.Colour.teal()
    warn = discord.Colour.teal()
    mute = discord.Colour.orange()
    kick = discord.Colour.red()
    softban = discord.Colour.red()
    ban = discord.Colour.dark_red()
    unban = discord.Colour.green()

    def __str__(self) -> str:
        return self.name

    def __int__(self) -> int:
        return int(self.value)


InfractionColor = InfractionColour

I = TypeVar('I', bound='InfractionEntry')

class InfractionEntry:
    def __init__(self, document: dict):
        self._document = document
        self._id: ObjectId = document['_id']
        self.type = InfractionType(document['type'])
        self.mod_id: int = document['moderator']
        self.offender_id: int = document['offender']
        self.time = self._id.generation_time
        self.id: int = document['id']
        self._until: Optional[Timestamp] = document.get('until', None)
        self._reason: str = document['reason']

    def __int__(self) -> int:
        return self.id

    def __eq__(self, o: object) -> bool:
        # why is this even here
        return isinstance(o, self.__class__) and o._id == self._id

    def __ne__(self, o: object) -> bool:
        # why is this even here
        return not self.__eq__(o)

    def __repr__(self) -> str:
        return (
            f'<InfractionEntry _id={self._id!r} id={self.id} type={self.type!r} '
            f'mod_id={self.mod_id} offender_id={self.offender_id} time={self.time!r} until={self.until}>'
        )

    def __str__(self) -> str: # "markdownified" version
        return (
            f'**Offender:** <@{self.offender_id}> `({self.offender_id})`\n'
            f'**Moderator:** <@{self.mod_id}> `({self.mod_id})`\n'
            f'**Reason:** {self._reason}'
        )

    @property
    def case(self) -> str:
        return f'Case #{self.id} | {self.type.name.capitalize()}'

    @property
    def until(self) -> Optional[Timestamp]:
        return self._until

    @until.setter
    def until(self, value):
        if not isinstance(value, (Timestamp, float)):
            raise TypeError(f'Expected a POSIX timestamp but recieved {value.__class__.__name__}')
        self._until = value

    @property
    def reason(self) -> str:
        return self._reason

    @reason.setter
    def reason(self, value: str):
        self._reason = value

    def to_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f'Case #{self.id} | {self.type.name.capitalize()}',
            description = self.__str__(),
            colour = int(InfractionColour[self.type.name]),
            timestamp = self.time
        )
        
        if self._until:
            embed.add_field(name='Valid Until', value=format_dt(datetime.datetime.fromtimestamp(self._until), 'F'))

        embed.set_footer(text='Infraction issued at')

        return embed

    def to_offender_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title = f'Case #{self.id} | {self.type.name.capitalize()}',
            description = f'**Reason:** {self.reason}',
            colour = InfractionColour[self.type.name].value,
            timestamp = self.time
        )

        if self._until:
            embed.add_field(name='Valid Until', value=format_dt(datetime.datetime.fromtimestamp(self._until), 'F'))

        embed.set_footer(text='Infraction issued at')

        return embed

    def to_small_embed(self) -> discord.Embed:
        embed = discord.Embed(
            colour = InfractionColour[self.type.name].value,
            description = f'<@{self.offender_id}> (`{self.offender_id}`) was infracted | **{self.type}**',
            timestamp = utcnow()
        )
        embed.set_footer(text=f'Case #{self.id}')

        return embed

    @property
    def entry(self) -> str:
        return (
            f'**Case #{self.id} | {self.type.name.capitalize()} | {self.time.strftime("%Y-%m-%d")}**\n'
            f'{self.__str__()}'
        )

class Embed(discord.Embed):
    def __init__(
        self,
        *,
        author: discord.User = None,
        footer: str = None,
        **kwargs
    ):
        super().__init__(**kwargs)

        if author:
            self.set_author(name=str(author), icon_url=author.avatar.url)
        if footer:
            self.set_footer(text=footer)

    async def post_log(self, bot: Bot, guild: discord.Guild = None, **kwargs) -> Optional[discord.Message]:
        settings = await bot.utils.find_one({'type':'settings'})
        channel_id = settings['log']

        if guild:
            channel = guild.get_channel(channel_id)
        else:
            channel = bot.get_channel(channel_id)

        if channel is None:
            return

        return await channel.send(embed=self, **kwargs)