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

import datetime
import json
import time
import discord
import pkg_resources
import utils
import psutil

from typing import Optional, Union
from collections import Counter
from discord.ext import commands
from jishaku.shim.paginator_200 import PaginatorEmbedInterface, PaginatorInterface

cache = utils.Cache(None)

TICKETLOGS = 671795168655048704
ROWIFIGUILD = 576325772629901312

def guild_info(user: Union[discord.Member, discord.User]):
    if isinstance(user, discord.User):
        return ''
    
    roles = user.roles
    roles.remove(user.guild.default_role)
    if roles:
        roles = ', '.join([r.mention for r in roles]) if len(roles) <= 7 else f'{len(roles)} roles'
    else:
        roles = ''

    info = f'**Joined:** {utils.format_date(user.joined_at)}\n'\
           f'**Roles:** {roles}'

    return info

class Info(commands.Cog, name='Information'):
    """The Information Module holds commands which are used to get info on someone or something."""
    def __init__(self, bot: utils.Bot):
        self.bot = bot
        self.process = psutil.Process()


    @utils.is_bot_channel()
    @commands.command(aliases=['ui'])
    async def userinfo(self, ctx: utils.Context, *, user: Optional[Union[discord.Member, discord.User]]):
        """Gives discord and roblox info on a user."""

        user = user or ctx.author

        embed = cache.get(user.id)
        if embed:
            if embed[0][1] == ctx.guild.id:
                return await ctx.send(embed=embed[0][0])

        is_verified = await utils.request(
            self.bot.session,
            'GET',
            f'https://api.rowifi.link/v1/users/{user.id}?guild_id={ctx.guild.id}'
        )

        if is_verified.get('success', False):
            r = await utils.request(self.bot.session, 'GET', f'https://users.roblox.com/v1/users/{is_verified.get("roblox_id")}')
            RoUser = utils.RoWifiUser(r, is_verified.get('discord_id'), is_verified.get('guild_id', None))
        else:
            RoUser = utils.FakeUser()

        embed = discord.Embed(
            title = 'User Information',
            colour = self.bot.colour,
            timestamp = utils.utcnow()
        )

        embed.set_author(name=str(user), icon_url=user.avatar.url)
        embed.set_footer(text=ctx.bot.footer)
        embed.set_thumbnail(url=RoUser.avatar_url)

        embed.add_field(
            name='Roblox Information',
            value=f'**Name:** {RoUser.name}\n'\
                  f'**ID:** {RoUser.id}\n'\
                  f'**Created:** {utils.format_date(RoUser.created_at)}',
            inline=False
        )

        embed.add_field(
            name='Discord Information',
            value=f'**Name:** {user.display_name}\n'\
                  f'**ID:** {user.id}\n'\
                  f'**Created At:** {utils.format_date(user.created_at)}\n'\
                  f'{guild_info(user)}',
            inline=False
        )

        if not isinstance(user, discord.Member):
            embed.description = '*This user is not in the current server.*'

        cache[user.id] = (embed, ctx.guild.id)

        await ctx.reply(embed=embed)

    @utils.is_bot_channel()
    @commands.command(aliases=['av'])
    async def avatar(self, ctx: utils.Context, *, user: Optional[discord.User]):
        """Displays avatar of the user."""
        user = user or ctx.author
        
        def url_as(format: str) -> str:
            return user.avatar.with_format(format).url
        
        embed = discord.Embed(
            title = f'Avatar for {user}',
            description=(
                f'Link As\n'\
                f'[png]({url_as("png")}) | [jpg]({url_as("jpg")}) | [webp]({url_as("webp")})'
            ),
            colour=ctx.bot.colour
        )
        
        embed.set_image(url=user.avatar.url)
        await ctx.reply(embed=embed)

    @utils.is_intern()
    @commands.command()
    async def notify(self, ctx: utils.Context, user: discord.Member, *, notification: str):
        """Notifies the user about the notification."""
        embed = discord.Embed(
            colour = ctx.author.colour,
            description = notification,
            timestamp = utils.utcnow()
        )

        embed.set_author(name='Notification from RoWifi Staff', icon_url='https://cdn.discordapp.com/emojis/733311296732266577.png?v=1')

        try:
            await user.send(embed=embed)
            await ctx.tick()
        except discord.Forbidden:
            await ctx.reply("Couldn't notify the user because they either have blocked me or have their DMs closed.")

        embed.add_field(name='Notification Sent to', value=f'{user.mention} - `{user.id}`')
        embed.set_footer(
            text=f'Sent from: {ctx.author} - {ctx.author.id}',
            icon_url=ctx.author.avatar.url
        )

        await utils.post_log(self.bot, ctx.guild, embed=embed)

    @utils.is_bot_channel()
    @commands.command()
    async def uig(self, ctx: utils.Context, user: Union[discord.User, int, str], group_id: int):
        """Checks if a user is in the given Roblox group."""

        if isinstance(user, discord.User):
            r = await utils.request(ctx.session, 'GET', f'https://api.rowifi.link/v1/users/{user.id}?guild_id={ctx.guild.id}')
            if r['success']:
                userId = r['roblox_id']
            else:
                return await ctx.reply('The given user is not verified with RoWifi and hence I cannot look up their roblox id.')

        elif isinstance(user, int):
            userId = user

        elif isinstance(user, str):

            r = await utils.request(
                ctx.session,
                'POST',
                'https://users.roblox.com/v1/usernames/users',
                data={'usernames':[user]}
            )

            if r['data']:
                userId = r['data'][0]['id']
            else:
                return await ctx.reply(f'Cannot find the user "{user}"')

        r = await utils.request(
            ctx.session,
            'GET',
            f'https://groups.roblox.com/v2/users/{userId}/groups/roles'
        )

        try:
            data = r['data']
        except KeyError:
            return await ctx.reply('Cannot lookup the given user\'s groups at the moment. Try again later?')
        else:
            user: dict =  await utils.request(ctx.session, 'GET', f'https://users.roblox.com/v1/users/{userId}')

            for g in data:
                if g['group']['id'] == group_id:
                    member = utils.Member(
                        {
                            'name':user['name'],
                            'id':user['id'],
                            'displayName':user['displayName'],
                            'role':{
                                'id':g['role']['id'],
                                'name':g['role']['name'],
                                'rank':g['role']['rank'],
                                'membercount':0
                            }
                        },
                        group_id
                    )
                    return await ctx.reply(f'{member} is in group with id {group_id}. They have the role: {member.role} (Rank: {member.role.rank})')
            name = user['name']
            return await ctx.reply(f'The given user "{name}" is not in the given group.')

    @uig.error
    async def uig_err(self, ctx: utils.Context, error: commands.CommandError):
        error = getattr(error, 'original', error)
        if isinstance(error, utils.HTTPException):
            url = error.response.url
            status = error.status
            json = error.json

            embed = discord.Embed(
                title = 'A Roblox side error occured',
                description = f'Message: {json["errors"][0]["message"]}',
                colour = discord.Colour.red(),
                timestamp = utils.utcnow()
            )

            embed.set_footer(text=f'Status Code: {status}')

            embed.add_field(name='Url', value=url, inline=False)
            embed.add_field(name='Raw Error', value=f'```json\n{json}```', inline=False)

            await ctx.send(embed=embed)

    @utils.is_bot_channel()
    @commands.command()
    async def ping(self, ctx: utils.Context):
        """Shows bot ping"""
        start = time.perf_counter()
        msg = await ctx.reply('Pinging...')
        end = time.perf_counter()
        duration = (end-start)*1000

        embed = discord.Embed(
            colour=ctx.colour
        )
        embed.add_field(
            name='<a:typing:828718094959640616> | Typing',
            value=f'`{duration:.2f}ms`'
        )
        embed.add_field(
            name='🔁 | Websocket',
            value=f'`{(self.bot.latency*1000):.2f}ms`'
        )

        await msg.edit(content=None, embed=embed)

    @utils.is_intern()
    @commands.group(invoke_without_command=True)
    async def ticket(self, ctx: utils.Context, *, member: discord.Member=None):
        """Shows tentative tickets handled by a user."""
        member = member or ctx.author
        now = utils.utcnow()
        if now.month == 1:
            after = datetime.datetime(now.year, 12, now.day, now.hour, now.minute, now.second, now.microsecond, now.tzinfo)
        else:
            after = datetime.datetime(now.year, now.month-1, now.day, now.hour, now.minute, now.second, now.microsecond, now.tzinfo)

        channel: discord.TextChannel = ctx.guild.get_channel(TICKETLOGS)
        if channel is None:
            return await ctx.send('Cannot get logs right now. Try again later?')

        types = []
        async for msg in channel.history(limit=None, after=after):
            if msg.embeds:
                e = msg.embeds[0]

                lines = e.fields[-1].value.split('\n')
                for line in lines:
                    try:
                        user = await commands.UserConverter().convert(ctx, line.strip().split()[2])
                    except:
                        pass
                    else:
                        if user.id == member.id:
                            types.append(e.fields[2].value)
                            break

        counter = Counter(types)
        total = sum([v for v in counter.values()])
        embed = discord.Embed(
            title=f'Tickets Handled by {member} ({total})',
            description='\n'.join(f'**{k}**: {v}' for k,v in counter.items()),
            colour=ctx.colour,
            timestamp=utils.utcnow()
        )

        embed.set_footer(text='These are just "tentative" and not final for judging.')

        embed.add_field(
            name='Duration',
            value=f'**From:** {utils.format_date(after)}\n**Until:** {utils.format_date(now)}',
            inline=False
        )

        await ctx.send(embed=embed)
            
    @utils.is_admin()
    @ticket.command()
    async def info(self, ctx: utils.Context, *, flags: utils.TicketFlag):
        """Gives a detailed info on a user and their ticket handling.
        
        Accepts either a user or role and a after argument which accepts date in the 
        format `yyyy-mm-dd`."""
        user = flags.user
        role = flags.role
        if user and role:
            return await ctx.send('Please give either user or role, not both.')
        elif not user and not role:
            return await ctx.send('Please give either a role or a user.')

        after = flags.after
        now = utils.utcnow()
        if after:
            try:
                after = datetime.datetime.strptime(after, '%Y-%m-%d')
            except:
                return await ctx.send('Invalid date format given, please give a format of: `yyyy-mm-dd`')

        else:
            if now.month == 1:
                after = datetime.datetime(now.year, 12, now.day, now.hour, now.minute, now.second, now.microsecond, now.tzinfo)
            else:
                after = datetime.datetime(now.year, now.month-1, now.day, now.hour, now.minute, now.second, now.microsecond, now.tzinfo)

        channel: discord.TextChannel = ctx.guild.get_channel(TICKETLOGS)
        if channel is None:
            return await ctx.send('Cannot get logs right now. Try again later?')

        if user:
            converter = commands.UserConverter()
        elif role:
            converter = commands.MemberConverter()
        entries = []
        async for msg in channel.history(limit=None, after=after):
            if msg.embeds:
                try:
                    e = msg.embeds[0]
                    panel = e.fields[2].value
                    number = e.fields[1].value.split('-')[-1]
                    url = e.fields[-2].value.replace(')', '(').split('(')[1]
                    display = f'[{panel} {number}]({url})'
                except IndexError:
                    pass
                
                lines = e.fields[-1].value.split('\n')
                for line in lines:
                    try:
                        person = await converter.convert(ctx, line.strip().split()[2])
                    except:
                        pass
                    else:
                        if user:
                            if user.id == person.id:
                                entries.append(display)
                        elif role and isinstance(person, discord.Member):
                            if role in person.roles:
                                entries.append(f'{display} - {person}')

        entries.sort(key=lambda s: s.split()[0])

        if role:
            entries.sort(key=lambda s: s.split('-')[-1])

        embed = discord.Embed(
            colour = discord.Colour.blue(),
            title = f'Showing tickets for `{user if user else f"@{role}"}`'
        )

        embed.add_field(
            name='Duration',
            value=f'**From:** {utils.format_date(after)}\n**Until:** {utils.format_date(now)}',
            inline=False
        )

        if len(entries) == 0:
            return await ctx.send(f'No tickets handled by `{user if user else f"@{role}"}`')

        paginator = commands.Paginator(prefix='', suffix='', max_size=2000)
        for i,t in enumerate(entries, 1):
            paginator.add_line(f'{i}. {t}')

        interface = PaginatorEmbedInterface(self.bot, paginator, owner=ctx.author, embed=embed)

        await interface.send_to(ctx)

    @info.error
    async def info_err(self, ctx: utils.Context, error: commands.CommandError):
        error = getattr(error, 'original', error)
        embed = discord.Embed(
            colour = discord.Colour.red(),
            title = 'An error occurred',
            timestamp = utils.utcnow()
        )
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar.url)
        embed.set_footer(text=str(ctx.message.content))

        if isinstance(error, commands.BadUnionArgument):
            embed.description = '\n'.join(str(e) for e in error.errors)
        elif isinstance(error, commands.RoleNotFound):
            embed.description = str(error)
        else:
            embed.description = str(error)
            embed.add_field(name='Args', value=error.args or 'No Args', inline=False)
            try:
                embed.add_field(name='Message', value=error.message, inline=False)
            except AttributeError:
                pass            
            await ctx.send(embed=embed)
            raise error
        await ctx.send(embed=embed)

    def format_commit(self, commit):
        gt = datetime.datetime.strptime(f"{commit['commit']['committer']['date']}", '%Y-%m-%dT%H:%M:%SZ')
        now = datetime.datetime.now()
        offset = now.timestamp() - (datetime.datetime.utcnow().timestamp() - gt.timestamp()) # I have no idea why this works
        
        # [`hash`](url) message (offset)
        return f"[`{commit['sha'][0:6]}`]({commit['html_url']}) {commit['commit']['message']} (<t:{int(offset)}:R>)"
        
    async def get_last_commits(self, count=3):

        if self.bot.version_info.releaselevel == 'final':
            branch = 'main'
        else:
            branch = 'dev'
        url = f'https://api.github.com/repos/ItsArtemiz/RoUtils/commits?sha={branch}'

        r = await utils.request(
            self.bot.session,
            'GET',
            url
        )

        return '\n'.join(self.format_commit(c) for c in r[:count])

    # https://api.github.com/repos/ItsArtemiz/RoUtils/commits?sha=branch

    @utils.is_bot_channel()
    @commands.command()
    async def about(self, ctx: utils.Context):
        """Gives info on the bot."""

        commits = await self.get_last_commits()

        embed = discord.Embed(
            title=f'RoUtils {ctx.version}',
            colour = ctx.colour,
            description = f'Latest Changes:\n{commits}'
        )

        version = pkg_resources.get_distribution('discord.py').version
        embed.set_footer(text=f'Made with discord.py v{version}', icon_url='http://i.imgur.com/5BFecvA.png')


        guild = self.bot.get_guild(ROWIFIGUILD)
        owner = guild.get_member(self.bot.owner_id)
        if not owner:
            owner = await guild.fetch_member(self.bot.owner_id)

        embed.set_author(name=str(owner), icon_url=owner.avatar.url)

        embed.add_field(name='Commands Loaded', value=f'{len(self.bot.commands)}')
        embed.add_field(name='Uptime', value=utils.format_dt(self.bot.uptime, 'R'))
        
        memory_usage = self.process.memory_full_info().uss / 1024**2
        cpu_usage = self.process.cpu_percent() / psutil.cpu_count()
        
        embed.add_field(name='Process', value=f'{memory_usage:.2f} MiB\n{cpu_usage:.2f}% CPU')
        await ctx.send(embed=embed)

    @utils.is_admin()
    @commands.group(invoke_without_command=True)
    async def role(self, ctx: utils.Context, member: commands.Greedy[discord.Member], role: commands.Greedy[discord.Role]):
        """Adds role(s) to member(s)
        
        You can provide multiple members and roles at once.
        """

        if member is None and role is None:
            return await ctx.send(f'Missing either member or role parameeter')

        for m in member:
            try:
                await m.add_roles(*role)
            except Exception as e:
                await ctx.send(e)

        await ctx.tick(True)

    @utils.is_admin()
    @role.command()
    async def remove(self, ctx: utils.Context, member: commands.Greedy[discord.Member], role: commands.Greedy[discord.Role]):
        """Removes role(s) from member(s)."""

        if member is None and role is None:
            return await ctx.send(f'Missing either member or role parameeter')

        for m in member:
            try:
                await m.remove_roles(*role)
            except Exception as e:
                await ctx.send(e)

        await ctx.tick(True)

    @utils.is_bot_channel()
    @role.command(name='info')
    async def role_info(self, ctx: utils.Context, *, role: discord.Role):
        """Gives info on the role given."""

        embed = discord.Embed(
            title='Role Info',
            colour=role.colour,
            timestamp=role.created_at,
            description=f'Name: {role.name}\n'\
                        f'ID: `{role.id}`\n'\
                        f'Members: {len(role.members)}\n'\
                        f'Colour: {role.colour}'
        )

        embed.set_footer(text='Created at')

        await ctx.send(embed=embed)

    @utils.is_bot_channel()
    @commands.command(aliases=['msgraw'], hidden=True)
    async def rawmsg(self, ctx: utils.Context, message: str):
        """Gets the raw contents of the message.
        
        You need to invoke the command in the same channel where the message is
        else you will need to provide the channel id as well.
        
        Usage:
        • Using only message id: `msgraw messageId`
        • Using channel and message id: `msgraw channelId-messageId`
        """

        try:
            channel, msg = message.split('-')
        except ValueError:
            channel = ctx.channel.id
            msg = message

        try:
            channel = int(channel)
            msg = int(msg)
        except Exception as e:
            return await ctx.send(e)

        try:
            r = await self.bot.http.get_message(channel, msg)
        except Exception as e:
            return await ctx.send(e)
        else:
            data = json.dumps(r, indent=4)
            
            paginator = commands.Paginator(prefix='```json\n', max_size=2000, linesep='')

            for d in data.split(','):
                paginator.add_line(d)

            embed = discord.Embed(colour=ctx.colour)

            interface = PaginatorEmbedInterface(self.bot, paginator, owner=ctx.author, embed=embed)
            await interface.send_to(ctx)
        

def setup(bot: utils.Bot):
    bot.add_cog(Info(bot))