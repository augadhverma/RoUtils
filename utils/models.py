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

from typing import Optional, Union
from discord.ext import commands, menus
from discord.ext.menus.views import ViewMenuPages

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

class ViedEmbedSource(menus.ListPageSource):
    def __init__(self, entries, *, per_page=10):
        super().__init__(entries, per_page=per_page)

    async def format_page(self, menu: menus.Menu, entries):
        maximum = self.get_max_pages()
        if maximum > 1:
            footer = f'Page {menu.current_page + 1}/{maximum} ({len(self.entries)} entries)'
            menu.embed.set_footer(text=footer)
        
        pages = []
        for index, entry in enumerate(entries, start=menu.current_page * self.per_page):
            pages.append(f'{index + 1}. {entry}')        

        menu.embed.description = '\n'.join(pages)
        return menu.embed

class ViewEmbedPages(ViewMenuPages, inherit_buttons=False):
    def __init__(self, source, embed=None, **kwargs):
        super().__init__(source=source, check_embeds=True, **kwargs)
        if embed:
            self.embed = embed
        else:
            self.embed = discord.Embed(colour=discord.Colour.blue())
    
    def _skip_when(self):
        return self.source.get_max_pages() <= 2
    
    def _skip_when_short(self):
        return self.source.get_max_pages() <=1

    @menus.button('\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}', position=menus.First(0), skip_if=_skip_when)
    async def rewind(self, payload):
        """Goes to first page."""
        await self.show_page(0)

    @menus.button('\N{BLACK LEFT-POINTING TRIANGLE}', position=menus.First(1), skip_if=_skip_when_short)
    async def back(self, interaction: discord.Interaction):
        """Goes to the previous page."""
        await self.show_checked_page(self.current_page - 1)

    @menus.button('\N{BLACK SQUARE FOR STOP}', position=menus.First(2))
    async def stop_menu(self, interaction: discord.Interaction):
        """Removes this message."""
        self.stop()

    @menus.button('\N{BLACK RIGHT-POINTING TRIANGLE}', position=menus.Last(0), skip_if=_skip_when_short)
    async def forward(self, interaction: discord.Interaction):
        """Goes to the next page."""
        await self.show_checked_page(self.current_page + 1)

    @menus.button('\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}', position=menus.Last(1), skip_if=_skip_when)
    async def fastforward(self, interaction: discord.Interaction):
        """Goes to the last page."""
        await self.show_page(self._source.get_max_pages() - 1)