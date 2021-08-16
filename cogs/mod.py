"""
The Information module - for some basic info.
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

import discord
import datetime
import utils
import re
import string
import random

from utils.checks import INTERN
from collections import Counter
from jishaku.paginators import PaginatorEmbedInterface
from typing import List, Optional, Tuple
from discord.ext import commands, tasks
from utils import InfractionEntry, InfractionType, Context
from humanize import naturaltime

HQINVITE = 'https://discord.gg/vkfasCRNuD'
TICKETCATEGORY = 680039943199784960

# Converters from https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/mod.py

def can_execute_action(ctx: utils.Context, user, target):
    return user.id == ctx.bot.owner_id or \
           user == ctx.guild.owner or \
           user.top_role > target.top_role and \
           user != target        

class MemberID(commands.Converter):
    async def convert(self, ctx: utils.Context, argument: str) -> discord.Member:
        try:
            m = await commands.MemberConverter().convert(ctx, argument)
        except commands.BadArgument:
            try:
                member_id = int(argument, base=10)
            except ValueError:
                raise commands.BadArgument(f'{argument} is not a valid member or member ID.') from None
            else:
                m = await ctx.bot.get_or_fetch_member(ctx.guild, member_id)
                if m is None:
                    m = await commands.UserConverter().convert(ctx, argument)
        if not can_execute_action(ctx, ctx.author, m):
            raise commands.BadArgument('You cannot do this action on this user due to role hierarchy.')
        return m

class ActionReason(commands.Converter):
    async def convert(self, ctx: utils.Context, argument: str) -> str:
        ret = await commands.clean_content().convert(ctx, argument)

        if len(ret) > 512:
            reason_max = 512 - len(ret) + len(argument)
            raise commands.BadArgument(f'Reason is too long ({len(argument)}/{reason_max})')
        return ret

class NewReason(ActionReason):
    async def convert(self, ctx: utils.Context, argument: str) -> str:
        ret = f'New Reason by {ctx.author} (ID: {ctx.author.id}): {argument}'
        return await super().convert(ctx, ret)

class BannedMember(commands.Converter):
    async def convert(self, ctx: utils.Context, argument: str) -> discord.User:
        if argument.isdigit():
            member_id = int(argument, base=10)
            try:
                return await ctx.guild.fetch_ban(discord.Object(id=member_id))
            except discord.NotFound:
                raise commands.BadArgument('This member has not been banned before.') from None

        ban_list = await ctx.guild.bans()
        entity = discord.utils.find(lambda u: str(u.user) == argument, ban_list)

        if entity is None:
            raise commands.BadArgument('This member has not been banned before.')
        return entity

class NoMuteRole(commands.CommandError):
    def __init__(self):
        super().__init__('No mute role has been set up or an invalid role has been setup')

class WarnsSelection(discord.ui.View):
    def __init__(self, *, timeout: Optional[float] = 30.0):
        super().__init__(timeout=timeout)
        self.value = None
    options = [
        discord.SelectOption(
            label = 'Warns given',
            value = 'moderator'
        ),
        discord.SelectOption(
            label = f'Warns recieved',
            value = 'offender'
        )
    ]

    @discord.ui.select(options=options)
    async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
        self.value = select.values[0]
        self.stop()

time_regex = re.compile("(?:(\d{1,5})(h|s|m|d))+?")
time_dict = {"h":3600, "s":1, "m":60, "d":86400}

class TimeConverter(commands.Converter):
    async def convert(self, ctx: Context, argument: str) -> float:
        argument = argument.lower()
        matches = re.findall(time_regex, argument)
        time = 0
        for v, k in matches:
            try:
                time += time_dict[k]*float(v)
            except KeyError:
                raise commands.BadArgument(f"{k} is an invalid time-key! h/m/s/d are valid!")
            except ValueError:
                raise commands.BadArgument(f"{v} is not a number!")

        return time

class Moderation(commands.Cog):
    def __init__(self, bot: utils.Bot):
        self.bot = bot
        self.infraction_check.start()

    async def get_id(self) -> int:
        all_infraction_ids: List[int] = []
        async for doc in self.bot.infractions.find({}):
            all_infraction_ids.append(doc['id'])

        if all_infraction_ids:
            return all_infraction_ids.pop()+1
        return 1

    async def create_infraction(
        self,
        type: InfractionType,
        moderator: discord.User,
        offender: discord.User,
        reason: str,
        until: Optional[float] = None
    ) -> InfractionEntry:
        
        document = {
            'type':type.value,
            'moderator': moderator.id,
            'offender': offender.id,
            'reason':reason
        }
        
        def get_seconds(**kwargs) -> float:
            return utils.utcnow().timestamp() + datetime.timedelta(**kwargs).total_seconds()

        if until is None:
            if type.value <= 2: #autowarn, automute, warn
                until = get_seconds(days=15)
            elif type.value == 3: # mute with no time
                until = get_seconds(hours=3)
            elif type.value in (4, 5): # kick and softban
                until = get_seconds(days=30)
            # ban and unban will be in the database forever idk why
        else:
            until = get_seconds(seconds=until)

        document['until'] = until
        document['id'] = await self.get_id()

        insert = await self.bot.infractions.insert_one(document)
        document['_id'] = insert.inserted_id
        return InfractionEntry(document)

    async def on_infraction(self, ctx: Context, member: discord.Member, original: InfractionEntry):
        """This will be called when a user is infracted."""

        
        # 3 or more infractions active - auto mute for 3 hours
        # 5 or more active infractions - kick from the server
        await ctx.send(embed=original.to_small_embed()) # Sends in the channel that a user was infracted
        await ctx.post_log(embed=original.to_embed()) # Posts in the log channel
        try:
            await member.send(embed=original.to_offender_embed()) # Tries to send the user their infraction
        except discord.HTTPException:
            await ctx.send('Cannot send the user the infraction notice', delete_after=5.0)

        documents = await self.bot.infractions.count_documents({'offender':member.id})

        async def infract_member(type: InfractionType, reason: str, until :float = None) -> Tuple[discord.Message, InfractionEntry]:
            infraction = await self.create_infraction(
                type=type,
                moderator=self.bot.user,
                offender=member,
                reason=reason,
                until=until
            )

            try:
                await member.send(embed=infraction.to_offender_embed())
            except discord.HTTPException:
                pass
            finally:
                post = await ctx.post_log(embed=infraction.to_embed())
                return post, infraction
        
        inf = None
        msg = None

        if documents > 5: # kick
            msg, inf = await infract_member(
                InfractionType.kick,
                f'You have been auto-kicked for achieving more than 5 infractions from RoWifi HQ. You may join using {HQINVITE}'
            )

            try:
                await member.kick(reason=f'Auto-kick for recieving {documents} infractions')
            except discord.HTTPException:
                return await ctx.send(f'Auto-mod failed to kick {member}, reached {documents} infractions.')


        elif documents >= 3: # automute
            settings = await self.bot.utils.find_one({'type':'settings'})
            role: discord.Role = ctx.guild.get_role(settings['muteRole'])
            if role is None:
                return await ctx.send(f'Please set a mute role, {member} crossed the infraction threshold and needs to be muted.')
            try:
                await member.add_roles(role, reason=f'Auto mute for reaching {documents} infractions')
            except discord.HTTPException:
                return await ctx.send(f'Auto-mod failed in adding mute role to {str(member)}, reached {documents} infractions.')

            msg, inf = await infract_member(
                InfractionType.automute,
                f'You have been auto-muted for 3 hours.',
                until=datetime.timedelta(hours=3).total_seconds()
            )

        if inf:
            await ctx.send(embed=inf.to_small_embed())
            return msg, inf
        else:
            return None, original

    @utils.is_staff()
    @commands.command()
    async def warn(self, ctx: Context, offender: commands.Greedy[discord.Member], *, reason: ActionReason):
        """Warns a user."""
        if ctx.replied_reference:
            message = await ctx.channel.fetch_message(ctx.replied_reference.message_id)
            offender = [message.author]
            
            await message.delete()

        await ctx.message.delete()
        for user in offender:
            if can_execute_action(ctx, ctx.author, user) is False:
                await ctx.send(f'Cannot do action on {user} due to role hierarchy.')
                continue
            infraction = await self.create_infraction(
                InfractionType.warn,
                ctx.author,
                user,
                reason
            )

            await self.on_infraction(ctx, user, infraction)

    @utils.is_staff()
    @commands.command()
    async def spam(self, ctx: Context, offender: commands.Greedy[discord.Member]):
        """Warns a user for spamming."""
        
        await ctx.invoke(self.warn, offender=offender, reason=f'Spamming in #{ctx.channel.name}')

    @utils.is_staff()
    @commands.command()
    async def bypass(self, ctx: Context, offender: commands.Greedy[discord.Member]):
        """Warns a user for bypassing or using a bad word."""
        await ctx.invoke(self.warn, offender=offender, reason=f'Bypassing a prohibited word in #{ctx.channel.name}')

    @utils.is_staff()
    @commands.command()
    async def info(self, ctx: Context, case: int):
        """Shows info on a case."""

        document = await self.bot.infractions.find_one({'id':case})
        if document is None:
            return await ctx.send(f'Could not find a case corresponding to the id {case}')

        infraction = InfractionEntry(document)

        await ctx.send(embed=infraction.to_embed())

    @utils.is_staff()
    @commands.command()
    async def warns(self, ctx: Context, user: Optional[discord.User]):
        """Shows all warns. If a user is given then shows on the basis of infractions
        given or recieved.
        """
        pages: List[InfractionEntry] = []
        if user is None:
            async for document in self.bot.infractions.find({}):
                pages.append(InfractionEntry(document))

        elif user:
            view = WarnsSelection()
            await ctx.send('Select an option', view=view)
            
            await view.wait()
            value = view.value
            if value is None:
                return await ctx.send('Aborting Command...')
            async for document in self.bot.infractions.find({value:user.id}):
                pages.append(InfractionEntry(document))

        if pages:
            embed = discord.Embed(title=f'{len(pages)} infractions found', colour=ctx.colour)
            paginator = commands.Paginator(prefix=None, suffix=None, max_size=1000, linesep='\n')
            for inf in pages:
                paginator.add_line(inf.entry, empty=True)

            interface = PaginatorEmbedInterface(self.bot, paginator, owner=ctx.author, embed=embed)

            await interface.send_to(ctx)

        else:
            await ctx.send('No infractions found.')

    @utils.is_staff()
    @commands.command()
    async def reason(self, ctx: Context, case: int, *, reason: NewReason):
        """Changes the reason of an existing case."""
        document = await self.bot.infractions.find_one({'id':case})
        if document is None:
            return await ctx.send(f'Could not find a case with id {case}')

        await self.bot.infractions.update_one(
            {'id':case},
            {'$set':{'reason':reason}}
        )

        await ctx.reply(f'Successfully changed the reason for case {case}')

    @utils.is_intern()
    @commands.command()
    async def nick(self, ctx: Context, member: discord.Member, *, nickname: Optional[commands.clean_content]):
        """Changes the nickname of a user."""
        await member.edit(nick=nickname)
        await ctx.tick(True)

    @utils.is_intern()
    @commands.command()
    async def mod(self, ctx: Context, member: commands.Greedy[discord.Member]):
        for m in member:
            await m.edit(nick=self.mod_name())
        await ctx.tick(True)        

    @utils.is_bot_channel()
    @commands.command(aliases=['warnings'])
    async def mywarns(self, ctx: Context):
        """Shows you your warn"""
        pages: List[InfractionEntry] = []
        async for document in self.bot.infractions.find({'offender':ctx.author.id}):
            pages.append(InfractionEntry(document))

        await ctx.send('Sending you a list of your infractions.')

        if pages:
            embed = discord.Embed(title=f'{len(pages)} infractions found', colour=ctx.colour)
            paginator = commands.Paginator(prefix=None, suffix=None, max_size=1000, linesep='\n\n')
            for inf in pages:
                paginator.add_line(inf.entry)

            interface = PaginatorEmbedInterface(self.bot, paginator, owner=ctx.author, embed=embed)

            try:
                await interface.send_to(ctx.author)
            except Exception as e:
                await ctx.send(e)

        else:
            await ctx.author.send('No infractions found.')

    @utils.is_staff(senior=True)
    @commands.command()
    async def kick(self, ctx: Context, offender: commands.Greedy[discord.Member], *, reason: ActionReason):
        """Kicks a user from the server."""

        await ctx.message.delete()
        for user in offender:
            if can_execute_action(ctx, ctx.author, user) is False:
                await ctx.send(f'Cannot do action on {user} due to role hierarchy.')
                continue
            infraction = await self.create_infraction(
                InfractionType.kick,
                ctx.author,
                user,
                reason
            )

            await self.on_infraction(ctx, user, infraction)

            try:
                await user.kick(reason=reason + f' | Moderator: {ctx.author} (ID: {ctx.author.id})')
            except discord.HTTPException:
                await ctx.send('Cannot kick the user. I may not have sufficient permissions.')

    @utils.is_staff(senior=True)
    @commands.command()
    async def ban(self, ctx: Context, offender: commands.Greedy[MemberID], *, reason: ActionReason):
        """Bans a user from the server."""

        await ctx.message.delete()
        for user in offender:
            if can_execute_action(ctx, ctx.author, user) is False:
                await ctx.send(f'Cannot do action on {user} due to role hierarchy.')
                continue
            infraction = await self.create_infraction(
                InfractionType.ban,
                ctx.author,
                user,
                reason
            )

            await self.on_infraction(ctx, user, infraction)

            try:
                await ctx.guild.ban(user, reason=reason+f' | Moderator {ctx.author} (ID: {ctx.author.id})', delete_message_days=7)
            except discord.HTTPException:
                await ctx.send('Cannot ban the user. I may not have sufficient permissions.')
    
    @utils.is_staff()
    @commands.command(aliases=['rw'])
    async def removewarn(self, ctx: Context, case: int, *, reason: str):
        """Removes a warn from the database."""

        infraction = await self.bot.infractions.find_one({'id':case})
        if infraction is None:
            return await ctx.send('No infraction found for the given case id.')
        
        infraction = InfractionEntry(infraction)

        await self.bot.infractions.delete_one({'id':case})
        await ctx.reply(f'Deleted the infraction with case id {case}.')

        await ctx.post_log(
            content=f'The following infraction (case #{case}) was removed by {ctx.author} ({ctx.author.id}) with reason:\n{reason}',
            embed=infraction.to_embed()
        )

    @utils.is_staff(senior=True)
    @commands.command(aliases=['cw'])
    async def clearwarns(self, ctx: Context, user: discord.User, *, reason: str):
        """Clears all warns for the user from the database."""

        deleted = await self.bot.infractions.delete_many({'offender':user.id})
        await ctx.send(f'Successfully deleted {deleted.deleted_count} infractions for {user} ({user.id}).')

        embed = discord.Embed(
            colour = discord.Colour.yellow(),
            title = 'Mutliple Infractions Removed',
            description = f'{deleted.deleted_count} infractions were removed by {ctx.author} ({ctx.author.id})',
            timestamp=utils.utcnow()
        )
        embed.add_field(name='Reason', value=reason, inline=False)

        await ctx.post_log(embed=embed)

    @utils.is_staff(senior=True)
    @commands.command()
    async def unban(self, ctx: Context, user: discord.User, *, reason: ActionReason):
        """Unbans a user."""
        try:
            entry = await ctx.guild.fetch_ban(user)
        except discord.HTTPException:
            return await ctx.send(f'The given user "{user}" has not been banned.')

        try:
            await ctx.guild.unban(user, reason=reason+f' | Moderator: {ctx.author} ({ctx.author.id}')
            await ctx.send(f'Previously banned for: {entry.reason}')
        except discord.HTTPException:
            return await ctx.send('Could not unban at the moment.')

        infraction = await self.create_infraction(
            InfractionType.unban,
            ctx.author,
            user,
            reason
        )

        await ctx.post_log(infraction.to_embed())

    @utils.is_staff(senior=True)
    @commands.command()
    async def softban(self, ctx: Context, offender: commands.Greedy[MemberID], *, reason: ActionReason):
        """Bans and immediately unbans the users"""

        await ctx.message.delete()
        audit_reason = reason+f' | Moderator: {ctx.author} ({ctx.author.id})'
        for user in offender:
            if can_execute_action(ctx, ctx.author, user) is False:
                await ctx.send(f'Cannot do action on {user} due to role hierarchy.')
                continue
            try:
                await ctx.guild.ban(user, reason=audit_reason, delete_message_days=7)
                await ctx.guild.unban(user, reason=audit_reason)
            except discord.HTTPException:
                return await ctx.send('Could not execute the action at the moment. Try again later?')
            infraction = await self.create_infraction(
                InfractionType.softban,
                ctx.author,
                user,
                reason
            )

            await ctx.send(embed=infraction.to_small_embed())
            await ctx.post_log(embed=infraction.to_embed())

    @utils.is_intern()
    @commands.command(aliases=['sm'])
    async def slowmode(self, ctx: Context, channel: Optional[discord.TextChannel], delay: Optional[str]):
        """Sets the slowmode for the channel given.
        If no channel is given, sets the slowmode for the current channel.
        
        If no delay is given, displays the current slowmode.
        """

        channel = channel or ctx.channel
        current_delay = channel.slowmode_delay

        await ctx.message.delete()

        if delay is None:
            return await ctx.send(f'Slowmode for #{channel} is {current_delay} seconds.')

        if delay.lower() in ('off', 'disable'):
            await channel.edit(slowmode_delay=0)
            await ctx.send(f'Alright, I have disabled the slowmode for #{channel}.')
        
        elif delay and (delay[0] in ('+', '-')):
            delay = current_delay + int(delay)
            if delay < 0:
                delay = 0
            elif delay > 21600:
                delay = 21600

            await channel.edit(slowmode_delay=delay)
            await ctx.send(f'Alright, I have set the slowmode for #{channel} to {delay} seconds.')

        elif delay:
            try:
                await channel.edit(slowmode_delay=int(delay))
                await ctx.send(f'Alright, I have set the slowmode for #{channel} to {delay} seconds.')
            except Exception as e:
                return await ctx.send(e)

    # Thanks to Danny for this :D
    # https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/mod.py#L1181-L1299

    async def do_removal(self, ctx, limit, predicate, *, before=None, after=None):
        if limit > 2000:
            return await ctx.send(f'Too many messages to search given ({limit}/2000)')

        if before is None:
            before = ctx.message
        else:
            before = discord.Object(id=before)

        if after is not None:
            after = discord.Object(id=after)

        try:
            deleted = await ctx.channel.purge(limit=limit, before=before, after=after, check=predicate)
        except discord.Forbidden as e:
            return await ctx.send('I do not have permissions to delete messages.')
        except discord.HTTPException as e:
            return await ctx.send(f'Error: {e} (try a smaller search?)')

        spammers = Counter(m.author.display_name for m in deleted)
        deleted = len(deleted)
        messages = [f'{deleted} message{" was" if deleted == 1 else "s were"} removed.']
        if deleted:
            messages.append('')
            spammers = sorted(spammers.items(), key=lambda t: t[1], reverse=True)
            messages.extend(f'**{name}**: {count}' for name, count in spammers)

        to_send = '\n'.join(messages)

        if len(to_send) > 2000:
            await ctx.send(f'Successfully removed {deleted} messages.', delete_after=10)
        else:
            await ctx.send(to_send, delete_after=10)
        await ctx.message.delete()

    @utils.is_staff()
    @commands.group()
    async def purge(self, ctx: Context, member: Optional[discord.Member], search: Optional[int]):
        """Removes messages that meet a criteria.
        
        When the command is done doing its work, you will get a message
        detailing which users got removed and how many messages got removed.
        """

        if member is None and search is None:
            return await ctx.send_help(ctx.command)

        else:
            if member:
                if search is None:
                    return await ctx.send('Missing the `search` parameter to search the number of messages to delete.')
                await ctx.invoke(self.user, member=member, search=search)
            elif search:
                await ctx.invoke(self.remove_all, search=search)

    @utils.is_staff()
    @purge.command()
    async def embeds(self, ctx:commands.Context, search=100):
        """Removes messages that have embeds in them."""
        await self.do_removal(ctx, search, lambda e: len(e.embeds))

    @utils.is_staff()
    @purge.command()
    async def files(self, ctx:commands.Context, search=100):
        """Removes messages that have attachments in them."""
        await self.do_removal(ctx, search, lambda e: len(e.attachments))

    @utils.is_staff()
    @purge.command()
    async def images(self, ctx:commands.Context, search=100):
        """Removes messages that have images in them."""
        await self.do_removal(ctx, search, lambda e: len(e.embeds) or len(e.attachments))

    @utils.is_staff()
    @purge.command(name='all')
    async def remove_all(self, ctx:commands.Context, search=100):
        """Removes all messages."""
        await self.do_removal(ctx, search, lambda e: True)

    @utils.is_staff()
    @purge.command(aliases=['member'])
    async def user(self, ctx:commands.Context, member:discord.Member, search=100):
        """Removes messages from a user."""
        await self.do_removal(ctx, search, lambda e: e.author == member)

    @utils.is_staff()
    @purge.command()
    async def contains(self, ctx:commands.Context, *, substr:str):
        """Removes messags that contain a string.
        The string to search should be atleast 3 characters long."""
        await self.do_removal(ctx, 100, lambda e: substr in e.content)

    @utils.is_staff()
    @purge.command(name='bot')
    async def _bot(self, ctx:commands.Context, prefix=None, search=100):
        """Removes messages by a bot with their optional prefix."""
        def pred(m):
            return (m.webhook_id is None and m.author.bot) or (prefix and m.content.startswith(prefix))

        await self.do_removal(ctx, search, pred)

    @utils.is_intern()
    @commands.command()
    async def cleanup(self, ctx:commands.Context, search=100):
        """Cleans up my messages."""
        await self.do_removal(ctx, search, lambda e: e.author == ctx.bot.user)

    @utils.is_staff()
    @commands.command(aliases=['m'])
    async def mute(self, ctx: Context, offender: commands.Greedy[discord.Member], time: TimeConverter, *, reason: ActionReason):
        """Mutes a user for the given amount of time. 
        By default mutes for three hours.
        Time should be of format: 1h 2d 3m 4s
        """
        await ctx.message.delete()
        settings = await self.bot.utils.find_one({'type':'settings'})

        role = ctx.guild.get_role(settings['muteRole'])
        if role is None:
            raise NoMuteRole()

        for user in offender:
            if can_execute_action(ctx, ctx.author, user) is False:
                await ctx.send(f'Cannot do action on {user} due to role hierarchy.')
                continue

            if role in user.roles:
                return await ctx.send('The given user is already muted.')

            try:
                await user.add_roles(role, reason=reason + f' | Moderator: {ctx.author} (ID: {ctx.author.id})')
            except discord.HTTPException:
                await ctx.send(f'Failed in adding the mute role to {user} (ID: {user.id})')
            else:
                infraction = await self.create_infraction(
                    InfractionType.mute,
                    ctx.author,
                    user,
                    reason,
                    time
                )

                await self.on_infraction(ctx, user, infraction)

    @mute.error
    async def mute_error(self, ctx: Context, error: commands.CommandError):
        if isinstance(error, commands.MissingRequiredArgument):
            if error.param.name == 'reason':
                args = ctx.args
                content = ctx.message.content
                return await ctx.invoke(self.mute, offender=args[2], time=10800, reason=content.split(' ')[-1])
            else:
                cmd = ctx.command
                return await ctx.reply(f'You forgot to provide the `{error.param.name}` argument while using the command. Refer `{ctx.clean_prefix}{cmd.qualified_name} {cmd.signature}`?')

        
        raise error

    @utils.is_staff()
    @commands.command()
    async def unmute(self, ctx: Context, member: commands.Greedy[discord.Member], *, reason: ActionReason):
        """Unmutes a user"""

        settings = await self.bot.utils.find_one({'type':'settings'})

        role = ctx.guild.get_role(settings['muteRole'])
        if role is None:
            raise NoMuteRole()

        for user in member:
            if role in user.roles:
                try:
                    await user.remove_roles(role, reason=reason + f' | Moderator: {ctx.author} (ID: {ctx.author.id})')
                except discord.HTTPException:
                    await ctx.send(f'Could not unmute {user}')
            else:
                await ctx.send(f'{user} is not muted.')

        await ctx.tick(True)

    @tasks.loop(minutes=1)
    async def infraction_check(self) -> None:
        settings = await self.bot.utils.find_one({'type':'settings'})
        if settings:
            mute_role_id = settings.get('muteRole')
            log = settings.get('log')
        else:
            mute_role_id = None
            log = None

        guild = self.bot.get_guild(576325772629901312)
        role = guild.get_role(mute_role_id)
        channel = guild.get_channel(log)

        async def post_log(**kwargs) -> Optional[discord.Message]:
            if channel is None:
                return
            if not isinstance(channel, discord.TextChannel):
                raise TypeError(f'expected discord.TextChannel but recieved {channel.__class__.__name__}')

            try:
                return await channel.send(**kwargs)
            except discord.HTTPException:
                return

        async def unmute(infraction: InfractionEntry):
            if role is None:
                return

            offender = guild.get_member(infraction.offender_id)
            if offender is None:
                try:
                    offender = await guild.fetch_member(infraction.offender_id)
                except discord.HTTPException:
                    return
                
            if role in offender.roles:
                time = infraction.time - datetime.datetime.fromtimestamp(infraction.until, datetime.timezone.utc)
                reason = f'Auto unmute after the mute given {naturaltime(time)}'
                try:
                    await offender.remove_roles(role, reason=reason)
                except discord.HTTPException:
                    return
                await post_log(content=reason, embed=infraction.to_embed())

        async for document in self.bot.infractions.find({}):
            document = InfractionEntry(document)
            
            until = document.until
            now = utils.utcnow().timestamp()
            if until is None:
                continue
            if not now >= until:
                continue

            if document.type.value in (1, 3):
                await unmute(document)

            await self.bot.infractions.delete_one({'_id':document._id})
            print(f'Document {document.id} was deleted.\nRepr: {repr(document)}\nDict: {document._document}')
            await post_log(content='Infraction Removed:',embed=document.to_embed())
        

    @infraction_check.before_loop
    async def before_infraction_check(self) -> None:
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignoring bots
        if message.author.bot:
            return

        # Ignore DMs
        if message.guild is None:
            return

        # Ignoring Staff
        if message.author.guild_permissions.manage_messages:
            return

        if INTERN in [r.id for r in message.author.roles]:
            return

        # Ignore autowarn in tickets
        if message.channel.category and message.channel.category_id == TICKETCATEGORY:
            return

        settings = await self.bot.utils.find_one({'type':'settings'})
        ctx = await self.bot.get_context(message, cls=Context)


        badwords: List[str] = settings['badWords']
        links: List[str] = settings['linkWhitelist']
        for word in badwords:
            regex = re.compile('\s*'.join(word), re.IGNORECASE)
            L = regex.findall(message.content)
            if L:
                try:
                    await message.delete()
                except discord.NotFound:
                    return

                infraction = await self.create_infraction(
                    InfractionType.autowarn,
                    self.bot.user,
                    message.author,
                    reason=f'Using a blacklisted word ({L[0]})'
                )

                await self.on_infraction(ctx, message.author, infraction)
                return
        
        url_regex = re.compile('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', re.IGNORECASE)

        for link in links:
            if link in message.content.lower():
                return
        else:
            L = url_regex.findall(message.content)
            if L:
                try:
                    await message.delete()
                except discord.NotFound:
                    return

                infraction = await self.create_infraction(
                    InfractionType.autowarn,
                    self.bot.user,
                    message.author,
                    reason=f'Using a blacklisted link ({L[0]})'
                )

                await self.on_infraction(ctx, message.author, infraction)
                return
        
        invite_regex = re.compile('(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?', re.IGNORECASE)

        L = invite_regex.findall(message.content)
        if L:
            try:
                invite = await commands.InviteConverter().convert(ctx, L[0])
                if invite.guild == ctx.guild:
                    return
            except commands.BadArgument:
                return
            else:
                try:
                    await message.delete()
                except discord.HTTPException:
                    return

                infraction = await self.create_infraction(
                    InfractionType.autowarn,
                    self.bot.user,
                    message.author,
                    reason=f'Using a blacklisted invite ({L[0]})'
                )

                await self.on_infraction(ctx, message.author, infraction)
                return
    @staticmethod
    def mod_name():
        letters = string.ascii_letters + string.digits
        return f'Moderated Nickname {"".join(random.sample(letters, k=10))}'

    async def check_member_name(self, member: discord.Member):
        name = self.mod_name()
        valid_letters = string.ascii_letters + string.digits
        valid_in_name = 0
        for L in member.display_name:
            if L in valid_letters:
                valid_in_name+=1

        if valid_in_name <= 3:
            await member.edit(nick=name)
            return

        settings = await self.bot.utils.find_one({'type':'settings'})
        badwords: List[str] = settings['badWords']
        for word in badwords:
            regex = re.compile('\s*'.join(word), re.IGNORECASE)
            L = regex.findall(member.display_name)
            if L:
                await member.edit(nick=name)
                return

    # @commands.Cog.listener()
    # async def on_member_join(self, member: discord.Member):
    #     await self.check_member_name(member)

    # @commands.Cog.listener()
    # async def on_member_update(self, before: discord.Member, after: discord.Member):
    #     await self.check_member_name(after)

def setup(bot: utils.Bot):
    bot.add_cog(Moderation(bot))