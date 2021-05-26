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

import asyncio
import time
import discord
import humanize
import string
import random

from typing import Counter, Optional
from discord.ext import commands, tasks, menus
from datetime import datetime
from bot import RoUtils

from utils.utils import InfractionEntry, InfractionType
from utils.db import MongoClient
from utils.checks import botchannel, staff, seniorstaff, intern
from utils.logging import infraction_embed, post_log
from utils.paginator import InfractionPages, SimpleInfractionPages, FieldPageSource, RoboPages
from utils.time import human_time

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
        try:
            await offender.send(embed=infraction_embed(entry=entry, offender=offender, show_mod=False))
        except discord.HTTPException:
            pass

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
            await offender.kick(reason=reason + f" | Moderator: {ctx.author}")
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
        await ctx.guild.ban(offender, reason=reason + f" | Moderator: {ctx.author}", delete_message_days =3)

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
        """Removes an infraction."""
        infraction = await self.db.find_one_and_delete({'id':id})
        if infraction:
            entry = InfractionEntry(data=infraction)
            user = self.bot.get_user(entry.offender_id)
            if not user:
                user = await self.bot.fetch_user(entry.offender_id)
            embed = infraction_embed(entry=entry, offender=user)

            embed.colour = discord.Colour.dark_grey()
            embed.title = embed.title + " | Infraction Removed"
            embed.add_field(name="Infraction Removed by", value=ctx.author.mention)
            embed.add_field(name="Reason for Removal", value=reason, inline=False)

            await ctx.send(content="Removed the Infraction:", embed=embed)

            await post_log(ctx.guild, name='bot-logs', embed=embed)

            try:
                await user.send(f"Infraction with id {entry.id} of type {entry.type} issued for reason: *{entry.reason}* has been removed.")
            except discord.HTTPException:
                pass


        else:
            return await ctx.send("Cannot find an infraction with the given id.")


    @staff()
    @commands.command(aliases=['cw'])
    async def clearwarns(self, ctx:commands.Context, user:discord.User, *, reason:str):
        await ctx.invoke(self.warns, user=user)

        def check(msg:discord.Message) -> bool:
            author = msg.author == ctx.author
            channel = msg.channel == ctx.channel
            answer = msg.content.lower() in ('yes', 'y')

            return author and channel and answer

        await ctx.send("Are you sure you want to delete all the infractions for the given user? Say `yes` if you want to.")

        try:
            message = await self.bot.wait_for('message', timeout=15.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send("Timeout Reached! Aborting...")
        else:
            deleted = await self.db.delete_many({'offender':user.id})

            await ctx.send(f"Successfully deleted {deleted.deleted_count} infraction for the given user.")

            embed = discord.Embed(
                title = "ALL INFRACTIONS REMOVED",
                colour = discord.Colour.dark_grey(),
                timestamp = datetime.utcnow()
            )
            embed.add_field(name='Removed by', value=f"{ctx.author.mention} `({ctx.author.id})`", inline=False)
            embed.add_field(name='Reason for Removal', value=reason, inline=False)
            embed.description = f"Removed {deleted.deleted_count} infractions for {user.mention} `({user.id})`"
            await post_log(ctx.guild, name='bot-logs', embed=embed)

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

        entry = await self.create_infraction(
            type=InfractionType.unban.value,
            moderator=ctx.author,
            offender=user,
            reason=reason
        )

        await ctx.guild.unban(user, reason=reason+f" | Moderator: {ctx.author}")

        embed = infraction_embed(entry=entry, offender=user, type="unbanned", small=True)
        embed.add_field(name="Previously banned for", value=isbanned.reason if isbanned.reason else 'No reason given.')

        await ctx.send(embed=embed)

        embed = infraction_embed(entry, user)
        embed.add_field(name="Previously banned for", value=isbanned.reason if isbanned.reason else 'No reason given.')

        await post_log(ctx.guild, name='bot-logs', embed=embed)

    @intern()
    @commands.command(aliases=['modlog'])
    async def info(self, ctx:commands.Context, id:int):
        """ Shows info of an infraction. """
        infraction = await self.db.find_one({'id':id})
        if infraction:
            entry = InfractionEntry(data=infraction)
            user = self.bot.get_user(entry.offender_id)
            if not user:
                user = await self.bot.fetch_user(entry.offender_id)
            embed = infraction_embed(entry=entry, offender=user)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"Cannot find the infraction with id {id} in the databse.")

    @staff()
    @commands.group(invoke_without_command=True, aliases=['guildbans'])
    async def bans(self, ctx:commands.Context, *, user:Optional[discord.User]):
        """ Shows all the bans in the server. """
        converted = []
        if not user:
            bans = await ctx.guild.bans()
            for ban in bans:
                converted.append((f"User: {ban.user}", f"Reason: {ban.reason or 'None provided...'}"))
        else:
            async for entry in ctx.guild.audit_logs(action=discord.AuditLogAction.ban):
                if entry.target.id == user.id:
                    converted.append(
                        (f"ID: {entry.id} | Moderator: {entry.user}",
                         f"Reason: {entry.reason or 'None provided...'}\nCreated At: {human_time(dt=entry.created_at, minimum_unit='minutes')}")
                    )
        if converted:
            try:
                p = RoboPages(FieldPageSource(converted, per_page=6))
            except menus.MenuError as e:
                await ctx.send(e)
            else:
                await p.start(ctx)
        else:
            await ctx.send("No bans to show.")


    @staff()
    @bans.command()
    async def by(self, ctx:commands.Context, moderator:discord.User):
        """ Bans made by a moderator. """
        converted = []
        async for entry in ctx.guild.audit_logs(action=discord.AuditLogAction.ban, user=moderator):
            converted.append(
                (f"ID: {entry.id} | User: {entry.target}",
                 f"Reason: {entry.reason or 'None provided...'}\nCreated At: {human_time(dt=entry.created_at, minimum_unit='minutes')}")
            )
        if converted:
            try:
                p = RoboPages(FieldPageSource(converted, per_page=6))
            except menus.MenuError as e:
                await ctx.send(e)
            else:
                await p.start(ctx)
        else:
            await ctx.send("No bans to show.")

    async def do_removal(self, ctx:commands.Context, limit:int, predicate, *, before=None, after=None):
        if limit > 2000:
            return await ctx.send(f"To many messages to search given ({limit}/2000)")

        if before is None:
            before = ctx.message
        else:
            before = discord.Object(id=before)

        if after is not None:
            after = discord.Object(id=after)

        try:
            deleted = await ctx.channel.purge(
                limit=limit, before=before, after=after, check=predicate
            )
        except discord.Forbidden:
            return await ctx.send("I do not have proper permissions to delete messages.")
        except discord.HTTPException as e:
            return await ctx.send(f"Error: {e} (try a smaller search?)")

        spammers = Counter(m.author.display_name for m in deleted)
        deleted = len(deleted)
        messages = [f'{deleted} message{" was" if deleted == 1 else "s were"} removed.']
        if deleted:
            messages.append('')
            spammers = sorted(spammers.items(), key=lambda t:t[1], reverse=True)
            messages.extend(f'**{name}**: {count}' for name, count in spammers)

        to_send = '\n'.join(messages)

        if len(to_send) > 2000:
            await ctx.send(f'Successfully removed {deleted} messages', delete_after=10.0)
        else:
            await ctx.send(to_send, delete_after=10.0)

        await ctx.message.delete()

    @staff()
    @commands.group(invoke_without_command=True, aliases=['remove'])
    async def purge(self, ctx:commands.Context, member:Optional[discord.Member], search:Optional[int]):
        """ Removes messages that meet a certain criteria.
        
        After the commmand has been executed, you will get
        a message detailing which users got removed and how
        many messages got removed.
        """
        if not member and not search and ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)
        else:
            if member:
                await ctx.invoke(self.user, member=member, search=search)
            elif search:
                await ctx.invoke(self._remove_all, search=search)

    @staff()
    @purge.command()
    async def embeds(self, ctx:commands.Context, search=100):
        """Removes messages that have embeds in them."""
        await self.do_removal(ctx, search, lambda e: len(e.embeds))

    @staff()
    @purge.command()
    async def files(self, ctx:commands.Context, search=100):
        """Removes messages that have attachments in them."""
        await self.do_removal(ctx, search, lambda e: len(e.attachments))

    @staff()
    @purge.command()
    async def images(self, ctx:commands.Context, search=100):
        """Removes messages that have images in them."""
        await self.do_removal(ctx, search, lambda e: len(e.embeds) or len(e.attachments))

    @staff()
    @purge.command(name='all')
    async def _remove_all(self, ctx:commands.Context, search=100):
        """Removes all messages."""
        await self.do_removal(ctx, search, lambda e: True)

    @staff()
    @purge.command(aliases=['member'])
    async def user(self, ctx:commands.Context, member:discord.Member, search=100):
        """Removes messages from a user."""
        await self.do_removal(ctx, search, lambda e: e.author == member)

    @staff()
    @purge.command()
    async def contains(self, ctx:commands.Context, *, substr:str):
        """Removes messags that contain a string.
        
        The string to search should be atleast 3 characters long."""
        await self.do_removal(ctx, 100, lambda e: substr in e.content)

    @staff()
    @purge.command(name='bot')
    async def _bot(self, ctx:commands.Context, prefix=None, search=100):
        """Removes messages by a bot with their optional prefix."""
        def pred(m):
            return (m.webhook_id is None and m.author.bot) or (prefix and m.content.startswith(prefix))

        await self.do_removal(ctx, search, pred)

    @intern()
    @commands.command()
    async def cleanup(self, ctx:commands.Context, search=100):
        """Cleans up my messages."""
        await self.do_removal(ctx, search, lambda e: e.author == ctx.bot.user)

    @seniorstaff()
    @commands.command()
    async def softban(self, ctx:commands.Context, offender:discord.Member, *, reason:str):
        """Bans and immediately unbans a user from the server."""
        await ctx.message.delete()

        if not self.hierarchy_check(ctx.author, offender):
            return await ctx.send('You cannot perform that action due to the hierarchy.')

        entry = await self.create_infraction(
            type=InfractionType.softban.value,
            moderator=ctx.author,
            offender=offender,
            reason=reason
        )

        embed = infraction_embed(entry, offender, 'softbanned', small=True)
        await ctx.send(embed=embed)

        try:
            await offender.send(embed=infraction_embed(entry, offender, show_mod=False))
        except discord.HTTPException:
            pass

        await ctx.guild.ban(offender, reason=reason + f" | Moderator: {ctx.author}", delete_message_days=3)
        await ctx.guild.unban(offender, reason=reason + f" | Moderator: {ctx.author}")

        await post_log(ctx.guild, name='bot-logs', embed=infraction_embed(entry, offender))

def setup(bot:RoUtils):
    bot.add_cog(Moderation(bot))
