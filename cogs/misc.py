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
from typing import Optional, Union

from utils.checks import admin, botchannel, intern
from utils.paginator import jskpagination

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
        if isinstance(message.channel, discord.DMChannel):
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

    @botchannel()
    @commands.command()
    async def ping(self, ctx:commands.Context):
        """ Shows bot ping. """

        start = time.perf_counter()
        m:discord.Message = await ctx.send('Pinging...')
        end = time.perf_counter()
        duration = (end-start)*1000

        embed = discord.Embed(
            colour = self.bot.invisible_colour
        )
        embed.add_field(
            name="<a:typing:828718094959640616> | Typing",
            value=f"`{duration:.2f}ms`"
        )
        embed.add_field(
            name="<:stab:828715097407881216> | Websocket",
            value=f"`{(self.bot.latency*1000):.2f}ms`"
        )

        tag_s = time.perf_counter()
        await self.bot.tag_db.count_documents({})
        tag_e = time.perf_counter()
        tag = (tag_e - tag_s)*1000

        mod_s = time.perf_counter()
        await self.bot.mod_db.count_documents({})
        mod_e = time.perf_counter()
        mod = (mod_e - mod_s)*1000

        embed.add_field(
            name='<:mongo:814706574928379914> | Database Connections',
            value=f'**Tags:** `{tag:.2f}ms` | **Moderation:** `{mod:.2f}ms`'
        )

        await m.edit(content=None, embed=embed)

    @botchannel()
    @commands.command()
    async def msgraw(self, ctx:commands.Context, message_id:int, channel_id:Optional[int]):
        """ Returns raw content of a message.
        If the message is from another channel, then you have to provide it aswell """

        channel_id = channel_id or ctx.channel.id

        content = await self.bot.http.get_message(channel_id=channel_id, message_id=message_id)

        await jskpagination(ctx, str(content), wrap_on=(','))

    @botchannel()
    @commands.command(aliases=['get_id'])
    async def getid(self, ctx:commands.Context, *, object:Union[discord.User, discord.Role, discord.TextChannel]):
        """ Gives you id of a role, user or text channel """
        try:
            await ctx.send(f"`{object.id}`")
        except commands.BadUnionArgument:
            await ctx.send(f"Cannot get id for {object}")

    @botchannel()
    @commands.command()
    async def news(self, ctx:commands.Context):
        """ Shows Bot News and Feature plans. """
        news = f"The"

        date = dt.datetime.utcnow().strftime('%B %d, %Y')

        embed = discord.Embed(
            title = f"\U0001f4f0 Latest News - {date} \U0001f4f0",
            description = news,
            colour = self.bot.invisible_colour
        )

        await ctx.send(embed=embed)

def setup(bot:RoUtils):
    bot.add_cog(Miscellaneous(bot))
