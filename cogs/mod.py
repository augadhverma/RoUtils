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
import humanize
import string
import random

from typing import Counter, Optional
from discord.ext import commands, tasks, menus
from bot import RoUtils

from utils.utils import InfractionEntry, InfractionType
from utils.db import MongoClient
from utils.checks import botchannel, staff, seniorstaff, intern
from utils.logging import infraction_embed, post_log
from utils.paginator import InfractionPages, SimpleInfractionPages

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

        await self.db.insert_one(document)
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

        await offender.send(embed=infraction_embed(entry=entry, offender=offender, show_mod=False))

    @staff()
    @commands.command()
    async def spam(self, ctx:commands.Context, *, offender:discord.Member):
        """ Warns a member for spamming. """
        await ctx.invoke(self.warn, offender=offender, reason=f"For spamming in #{ctx.channel.name}")

    @staff()
    @commands.command()
    async def bypass(self, ctx:commands.Context, *, offender:discord.Member):
        """ Warns a member for bypassing chat filter. """
        await ctx.invoke(self.warn, offender=offender, reason=f"For bypassing in #{ctx.channel.name}")

    @seniorstaff()
    @commands.command()
    async def kick(self, ctx:commands.Context, offender:discord.Member, *,reason:commands.clean_content):
        """ Kicks a user from the server. """
        await ctx.message.delete()

        if not self.hierarchy_check(ctx.author, offender):
            return await ctx.send('You cannot perform that action due to the hierarchy.')

        entry = await self.create_infraction(
            type=InfractionType.kick.value,
            moderator=ctx.author,
            offender=offender,
            reason=reason
        )
        embed = infraction_embed(entry=entry, offender=offender, type="kicked", small=True)

        await ctx.send(embed=embed)
        try:
            await offender.send(embed=infraction_embed(entry=entry, offender=offender, show_mod=False))
        except discord.HTTPException:
            pass
        try:
            await offender.kick(reason=reason)
        except discord.Forbidden:
            await ctx.send("Cannot Kick This User •.•")

        embed = infraction_embed(entry=entry, offender=offender)

        await post_log(ctx.guild, name='bot-logs', embed=embed)

    @seniorstaff()
    @commands.command()
    async def ban(self, ctx:commands.Context, offender:discord.User, *,reason:commands.clean_content):
        """ Bans a user from the server. """
        await ctx.message.delete()

        if not self.hierarchy_check(ctx.author, offender):
            return await ctx.send('You cannot perform that action due to the hierarchy.')

        entry = await self.create_infraction(
            type=InfractionType.ban.value,
            moderator=ctx.author,
            offender=offender,
            reason=reason
        )
        embed = infraction_embed(entry=entry, offender=offender, type="banned", small=True)

        await ctx.send(embed=embed)
        try:
            await offender.send(embed=infraction_embed(entry=entry, offender=offender, show_mod=False))
            await offender.send("Ban Appeal Form: https://forms.gle/5nPGXqiReY7SEHwv8")
        except discord.HTTPException:
            pass
        await ctx.guild.ban(offender, reason=reason, delete_days=3)

        embed = infraction_embed(entry=entry, offender=offender)

        await post_log(ctx.guild, name='bot-logs', embed=embed)

    @intern()
    @commands.command(aliases=['sm'])
    async def slowmode(self, ctx:commands.Context, channel:Optional[discord.TextChannel], delay:Optional[int]):
        """ Sets the slowmode of the channel given. If no channel is given, current one is used.
        If no delay is give, it shows the current slowmode of the channel.

        NOTE: The delay should be given in seconds.
        """

        channel = channel or ctx.channel

        if delay is None:
            return await ctx.send(f"The current slowmode is **{humanize.intcomma(channel.slowmode_delay)}** seconds.")

        elif delay>21600:
            return await ctx.send("You cannot set a slowmode more than 6 hours (21600 seconds).")

        else:
            await channel.edit(slowmode_delay=delay)
            return await ctx.send(f"Succesfully set the slowmode to **{humanize.intcomma(delay)}** seconds.")

    @staff()
    @commands.group(invoke_without_command=True)
    async def warns(self, ctx:commands.Context, *,user:Optional[discord.User]):
        """ Shows all warns.
        If a user is given, shows the warns given to the user.
        """
        pages = []
        if user:
            _all = self.db.find({'offender':user.id})
            async for doc in _all:
                pages.append(doc)
        else:
            _all = self.db.find({})
            async for doc in _all:
                pages.append(doc)
        if not pages:
            return await ctx.send("No warns to show.")

        try:
            p = InfractionPages(pages, per_page=6, show_mod=True)
        except menus.MenuError as e:
            await ctx.send(e)
        else:
            await p.start(ctx)

    @staff()
    @warns.command()
    async def by(self, ctx:commands.Context, *,moderator:Optional[discord.User]):
        """ Shows warnings by a moderator. """
        container = []
        if moderator:
            _all = self.db.find({'moderator':moderator.id})
            async for doc in _all:
                container.append(doc)
            if container:
                try:
                    p = InfractionPages(container, per_page=6, show_mod=True)
                except menus.MenuError as e:
                    await ctx.send(e)
                else:
                    await p.start(ctx)
            else:
                await ctx.send("No infractions have been made by the given user.")
        else:
            mods = []
            _all = self.db.find({})
            async for inf in _all:
                mods.append(inf['moderator'])
            for mod, infs in Counter(mods).items():
                container.append(f"<@{mod}> has made `{infs}` infractions.")

            if container:
                try:
                    p = SimpleInfractionPages(container)
                except menus.MenuError as e:
                    await ctx.send(e)
                else:
                    await p.start(ctx)
            else:
                await ctx.send("No infractions have been made.")

    @botchannel()
    @commands.command()
    async def mywarns(self, ctx:commands.Context):
        """ Shows you your warns. """
        await ctx.message.add_reaction("\U00002705")
        try:
            dm = await ctx.author.send("Sending you a list of your infractions.")
        except discord.Forbidden:
            return await ctx.send("I do not have the permissions to DM you!", delete_after=5.0)
        pages = []
        async for doc in self.db.find({'offender':ctx.author.id}):
            pages.append(doc)

        if pages:
            try:
                p = InfractionPages(pages, show_mod=False)
            except menus.MenuError as e:
                await ctx.send(e)
            else:
                await p.start(ctx, channel=dm.channel)
        else:
            await ctx.author.send("You don't have any active infractions.")

    @staff()
    @commands.command(aliases=['rw'])
    async def removewarn(self, ctx:commands.Context, id:int, *, reason:str):
        pass

    @staff()
    @commands.command(aliases=['cw'])
    async def clearwarns(self, ctx:commands.Context, user:discord.User, *, reason:str):
        pass
    

    @intern()
    @commands.command()
    async def nick(self, ctx:commands.Context, user:discord.Member, *, nick:str=None):
        """ Changes a user's nickname. """
        try:
            await user.edit(nick=nick)
            await ctx.message.add_reaction("\U00002705")
        except discord.Forbidden:
            await ctx.send("I do not have proper permissions to do that action!")

    @intern()
    @commands.command()
    async def mod(self, ctx:commands.Context, *, user:discord.Member):
        """ Changes a user's nickname to a Moderated Nickname. """
        await ctx.invoke(self.nick, user=user, nick="Moderated Nickname "+"".join(random.sample(string.ascii_letters+string.digits, k=8)))

    @seniorstaff()
    @commands.command()
    async def unban(self, ctx:commands.Context, user:discord.User, *, reason:str):
        """ Unbans a user from the guild. """
        try:
            isbanned = await ctx.guild.fetch_ban(user)
        except discord.NotFound:
            await ctx.send("The given user is not banned.")

        entry = self.create_infraction(
            type=InfractionType.unban.value,
            moderator=ctx.author,
            offender=user,
            reason=reason
        )

        await ctx.guild.unban(user, reason=reason+f" | Moderator: {ctx.author}")
        await ctx.send(f"Successfully unbanned **{isbanned.user}**.\nPreviously banned for: {isbanned.reason}")

        # Needs to log and DM User

def setup(bot:RoUtils):
    bot.add_cog(Moderation(bot))
