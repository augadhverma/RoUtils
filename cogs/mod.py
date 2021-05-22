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
from typing import Optional
import discord

from discord.ext import commands, tasks, menus
from bot import RoUtils

from utils.utils import InfractionEntry, InfractionType
from utils.db import MongoClient
from utils.checks import staff, seniorstaff, intern
from utils.logging import infraction_embed, post_log

class Moderation(commands.Cog):
    def __init__(self, bot:RoUtils):
        self.bot = bot
        self.db = MongoClient(db="Utilities", collection="Infractions")

    def hierarchy_check(self, moderator:discord.Member, offender:discord.Member) -> bool:
        owner = 449897807936225290
        if moderator.id == owner:
            return True

        elif offender.id == owner:
            return False

        elif moderator.top_role <= offender.top_role:
            return False

        elif offender.bot:
            return False

        return True

    async def get_new_id(self) -> int:
        _all = []
        async for doc in self.db.find({}):
            _all.append(doc)
        if _all:
            return (_all.pop())['id']+1
        else:
            return 1

    async def create_infraction(self, **kwargs) -> InfractionEntry:
        t = kwargs.get('type')
        until = kwargs.get('until', None)
        if (t <= 2) and (until is None):
            until = time.time() + 1296000 # warn, automute & autokick will be in db for 15 days.
        elif (t == 3) and (until is None):
            until = time.time() + 10800 # if no time is passed to mute, by default 3 hours is chosen.
        elif t in (4, 5):
            until = time.time() + 2592000 # kick & softban will be in db for 30 days.

        # ban & unban will be a permanent record of the user.

        document = {
            'type':t,
            'moderator':kwargs.get('moderator').id,
            'offender':kwargs.get('offender').id,
            'time':time.time(),
            'until':until,
            'reason':kwargs.get('reason'),
            'id':await self.get_new_id()
        }

        # await self.db.insert_one(document)
        return InfractionEntry(data=document)

    @staff()
    @commands.command()
    async def warn(self, ctx:commands.Context, offender:discord.Member, *, reason:commands.clean_content):
        """ Warns a user. """
        await ctx.message.delete()

        if not self.hierarchy_check(ctx.author, offender):
            return await ctx.send('You cannot perform that action due to the hierarchy.')

        entry = await self.create_infraction(
            type=InfractionType.warn.value,
            moderator=ctx.author,
            offender=offender,
            reason=reason
        )

        embed = infraction_embed(entry=entry, offender=offender, type="warned", small=True)

        await ctx.send(embed=embed)

        embed = infraction_embed(entry=entry, offender=offender)

        await post_log(ctx.guild, name='bot-logs', embed=embed)

    async def shows_warns(self, ctx:commands.Context, filter:dict):
        _all = self.db.find(filter)
        

    @staff()
    @commands.group(invoke_without_command=True)
    async def warns(self, ctx:commands.Context, user:Optional[discord.User]):
        """ Shows all warns. If a user is given, show's the user's warn. """

def setup(bot:RoUtils):
    bot.add_cog(Moderation(bot))