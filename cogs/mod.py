"""
Moderation Stuff.

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

import time
import discord

from discord.ext import commands, tasks, menus
from bot import RoUtils

from utils.utils import InfractionEntry, InfractionType
from utils.db import MongoClient

class Moderation(commands.Cog):
    def __init__(self, bot:RoUtils):
        self.bot = bot
        self.db = MongoClient(db="Utilities", collection="Infractions")

    async def get_new_id(self) -> int:
        _all = []
        async for doc in self.db.find({}):
            _all.append(doc)
        if _all:
            return (_all.pop())['id']+1
        else:
            return 1

    async def create_infraction(self, **kwargs):
        t = kwargs.get('type')
        until = kwargs.get('until', None)
        if t.value <= 2 and until is None:
            until = time.time() + 1296000

        document = {
            'type':t.value,
            'moderator':kwargs.get('moderator').id,
            'offender':kwargs.get('offernder').id,
            'time':time.time(),
            'until':until,
            'reason':kwargs.get('reason'),
            'id':await self.get_new_id()
        }