"""
Tags and stuff.

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

from typing import Union
from utils.db import MongoClient
import discord

from discord.ext import commands
from discord.ext.commands import bot
from bot import RoUtils

from utils.checks import botchannel, staff
from utils.utils import TagEntry


class Tags(commands.Cog):
    def __init__(self, bot:RoUtils):
        self.bot = bot
        self._cache = dict()
        self.db = MongoClient(db="Utilities", collection="Tags")

    @commands.command()
    async def tag(self, ctx:commands.Context, *, name):
        tag = self._cache.get(name, None)
        if tag is None:
            tag = TagEntry(data=await self.db.find_one({'name':name}))
            self._cache[name] = tag
        await ctx.send(repr(tag))

def setup(bot):
    bot.add_cog(Tags(bot))