"""
Miscellaneous Commands.

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

import discord
import time
import datetime as dt
import humanize

from bot import RoUtils
from discord.ext import commands

from utils.checks import admin, intern

class Miscellaneous(commands.Cog):
    def __init__(self, bot:RoUtils):
        self.bot = bot
        self._afk = dict()

    @intern()
    @commands.group(invoke_without_command=True)
    async def afk(self, ctx:commands.Context, *,reason:commands.clean_content=None):
        """ Sets an AFK status for maximum 24 hours """

        reason = reason or "Gone for idk how much long."

        d = self._afk.get(ctx.author.id, None)
        if d is None:
            self._afk[ctx.author.id] = (time.time(), reason)
        else:
            return await ctx.reply("You are already AFK'ed")

        await ctx.reply(f"Alright {ctx.author.name}, I have set your AFK.", delete_after=5.0)

    @admin()
    @afk.command(name="list")
    async def afklist(self, ctx:commands.Command):
        await ctx.send(self._afk)

    @admin()
    @afk.command(name="remove")
    async def afkremove(self, ctx:commands.Context, *, user:discord.User):
        if user.id in list(self._afk.keys()):
            del self._afk[user.id]
            await ctx.send(f"Succesfully removed {user.name} from the afk list.")
        else:
            await ctx.send("That user is not currently AFKed.")

    @admin()
    @afk.command(name="set")
    async def setafk(self, ctx:commands.Context, user:discord.User, *,reason:commands.clean_content):
        d = self._afk.get(user.id, None)
        if d is None:
            self._afk[user.id] = (time.time(), reason)
        else:
            return await ctx.reply("You are already AFK'ed")

        await ctx.reply(f"Alright {user.name}, I have set your AFK.", delete_after=5.0)


    @commands.Cog.listener()
    async def on_message(self, message:discord.Message):
        if message.channel.guild is None:
            return

        if message.author.bot:
            return

        user = self._afk.get(message.author.id, None)
        if user is not None:
            if (time.time() - user[0]) <= 5.0:
                pass
            else:
                await message.channel.send(f"{message.author.mention} I have removed your AFK status", delete_after=5.0)

                del self._afk[message.author.id]

        for user in message.mentions:
            afked = self._afk.get(user.id, None)
            if afked is None:
                pass
            else:
                await message.channel.send(f"{message.author.mention}, {user.name} has been AFK for {humanize.naturaldelta(dt.timedelta(seconds=time.time() - afked[0]))} with reason: {afked[1]}")
        


def setup(bot:RoUtils):
    bot.add_cog(Miscellaneous(bot))