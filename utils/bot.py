"""
The actual bot.
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
import sys
import traceback
import aiohttp
import discord
import os

from discord.ext import commands
from typing import NamedTuple, Optional
from dotenv import load_dotenv
from utils.context import Context
from .db import Client


load_dotenv()

URI = os.environ.get('DB_TOKEN')
TOKEN = os.environ.get('BOT_TOKEN')

os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True" 
os.environ["JISHAKU_HIDE"] = "True"

initial_extensions = {
    'jishaku',
    'cogs.info',
    'cogs.settings',
    'cogs.tags',
    'cogs.mod',
    'cogs.api',
    'cogs.logs',
    'cogs.handler',
    'cogs.help',
    'cogs.apps'
}

class VersionInfo(NamedTuple):
	major: int
	minor: int
	micro: int
	releaselevel: str
	serial: int

async def get_pre(bot, message: discord.Message):
    base = []
    if message.guild is None:
        base.append('.')

    else:
        settings: dict = await bot.utils.find_one({'type':'settings'})
        prefixes = settings.get('prefixes', [])
        base.extend(prefixes)

    if bot.version_info.releaselevel != 'final':
        base.extend(['b.', 'b!'])

    return commands.when_mentioned_or(*base)(bot, message)

class Bot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True

        super().__init__(
            command_prefix=get_pre,
            strip_after_prefix=True,
            allowed_mentions=discord.AllowedMentions.none(),
            owner_id=449897807936225290,
            case_insensitive=True,
            intents=intents,
        )

        self.loop.create_task(self.create_session())

        self.colour = discord.Colour.blue()
        self.footer = 'RoUtils'

        self.version_info = VersionInfo(major=2, minor=0, micro=2, releaselevel='final', serial=0)
        self.__version__ = '2.0.2'

        for cog in initial_extensions:
            try:
                self.load_extension(cog)
            except Exception:
                print(f'Failed to load extension {cog}', file=sys.stderr)
                traceback.print_exc()

    async def get_context(self, message, *, cls=None):
        return await super().get_context(message, cls=Context)

    async def create_session(self) -> None:
        db = 'Utilities'
        if not hasattr(self, 'session'):
            self.session = aiohttp.ClientSession(loop=self.loop)
        if not hasattr(self, 'tags'):
            self.tags = Client(URI, db, 'Tags')
        if not hasattr(self, 'infractions'):
            self.infractions = Client(URI, db, 'Infractions')
        if not hasattr(self, 'utils'):
            self.utils = Client(URI, db, 'Utils')
        if not hasattr(self, 'errors'):
            self.errors = Client(URI, db, 'Errors')
            
    async def on_ready(self) -> None:
        print(f'Ready {self.user} (ID: {self.user.id})')

        if not hasattr(self, 'uptime'):
            self.uptime = discord.utils.utcnow()

    async def close(self):
        await super().close()
        await self.session.close()

    def run(self):
        return super().run(TOKEN, reconnect=True)

    async def get_or_fetch_member(self, guild: discord.Guild, member_id: int) -> Optional[discord.Member]:
        """Looks up a member in cache or fetches if not found.

        Parameters
        ----------
        guild : discord.Guild
            The guild to look in.
        member_id : int
            The member ID to search for.

        Returns
        -------
        Optional[discord.Member]
            The member or None if not found.
        """
        member = guild.get_member(member_id)
        if member:
            return member

        try:
            member = await guild.fetch_member(member_id)
        except discord.HTTPException:
            return None
        else:
            return member