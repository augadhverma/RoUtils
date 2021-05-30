"""
The main file used to initiate the bot.

Copyright (C) 2021  ItsArtemiz (Augadh Verma)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>
"""

import os
from utils.db import MongoClient
import discord
import aiohttp
import datetime
import sys
import traceback

from discord.ext import commands
from typing import Optional

# Loads all the local environment variables
from dotenv import load_dotenv
load_dotenv()


prefixes = ('.',)

os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
os.environ["JISHAKU_HIDE"] = "True"

extensions = (
    'cogs.raw',
    'cogs.info',
    'cogs.help',
    'cogs.errorhandler',
    'cogs.config',
    'cogs.misc',
    'cogs.tags',
    'cogs.mod',
    'cogs.events'
)

class RoUtils(commands.Bot):
    def __init__(self, *args, **kwargs):
        allowed_mentions = discord.AllowedMentions(everyone=False, users=True, roles=False, replied_user=True)
        intents = discord.Intents(bans=True, messages=True, members=True, guilds=True, reactions=True)

        super().__init__(
            command_prefix=commands.when_mentioned_or(*prefixes),
            intents=intents,
            allowed_mentions=allowed_mentions,
            case_insensitive=True,
            strip_after_prefix=True,
            **kwargs
        )

        self.colour = discord.Colour.from_rgb(122, 219, 193)
        self.footer = "RoUtils"
        self.invisible_colour = 0x2F3136
        self.loop.create_task(self.create_session())
        self.version = "1.2.0b"

        if not hasattr(self, 'mod_db'):
            self.mod_db = MongoClient(db="Utilities", collection="Infractions")
        if not hasattr(self, 'tag_db'):
            self.tag_db = MongoClient(db="Utilities", collection="Tags")
        if not hasattr(self, 'utils'):
            self.utils = MongoClient(db='Utilities', collection='Utils')

        for cog in extensions:
            cog:str
            try:
                self.load_extension(cog)
            except Exception as e:
                print(f"Failed to load extension {cog}.", file=sys.stderr)
                traceback.print_exc()

        self.load_extension("jishaku")

    async def create_session(self):
        await self.wait_until_ready()
        if not hasattr(self, "session"):
            self.session = aiohttp.ClientSession()


    async def get_or_fetch_member(self, guild:discord.Guild, member_id:int) -> Optional[discord.Member]:
        """Gets a member from the cache, if not found in cache, makes an API call. If the member is not found, `None` is returned.

        Parameters
        ----------
        guild : discord.Guild
            The guild to search in.
        member_id : int
            The id of the member to search for.

        Returns
        -------
        Optional[discord.Member]
            The `Member` if found else `None`
        """
        member = guild.get_member(user_id=member_id)
        if member:
            return member

        try:
            member = await guild.fetch_member(member_id=member_id)
        except discord.HTTPException:
            return None
        else:
            return member

    async def on_ready(self) -> None:
        print(f"{self.user} is up and now running! (ID: {self.user.id})")

        if not hasattr(self, "uptime"):
            self.uptime = datetime.datetime.utcnow()

        if not hasattr(self, "footer"):
            self.footer = self.user.name

        if not hasattr(self, "colour"):
            self.colour = discord.Colour.blue()


if __name__ == "__main__":
    bot = RoUtils()
    bot.run(os.environ.get("BOT_TOKEN"))
