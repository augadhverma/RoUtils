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
import time
import discord
import pkg_resources
import utils
import psutil

from typing import Optional, Union
from collections import Counter
from discord.ext import commands
from jishaku.paginators import PaginatorEmbedInterface

cache = utils.Cache(None)

TICKETLOGS = 671795168655048704
ROWIFIGUILD = 576325772629901312
TICKETCATEGORY = 680039943199784960

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
    async def notify(
        self,
        ctx: utils.Context,
        member: Optional[discord.Member],
        channel: Optional[discord.TextChannel],
        *,
        notification: Optional[str]
    ):
        """Notifies the user about something."""

        if member and not notification:
            return await ctx.send("Please include the notification aswell.")

        elif channel:
            if channel.category and channel.category_id == TICKETCATEGORY:
                async for message in channel.history(oldest_first=True):
                    if message.embeds:
                        for word in message.embeds[0].description.split():
                            try:
                                member = await commands.MemberConverter().convert(ctx, word)
                                if notification is None:
                                    notification = f"Your ticket {channel.mention} has been inactive for a while. Please respond in the ticket so our team can take further actions."
                            except commands.BadArgument:
                                pass
                            else:
                                break
                    else:
                        return await ctx.send("Could not find the user.")
                    break
            else:
                return await ctx.send("Channel based notifications are only for ticket channels.")

        if member is None:
            return await ctx.send("Could not find the user.")

        embed = discord.Embed(
            colour = ctx.author.colour,
            description = notification,
            timestamp = utils.utcnow()
        )

        embed.set_author(name='Notification from RoWifi Staff', icon_url='https://cdn.discordapp.com/emojis/733311296732266577.png?v=1')

        try:
            await member.send(embed=embed)
            await ctx.tick()
        except discord.Forbidden:
            await ctx.send("Could not notify the user at this time. They either have DMs closed or have blocked me.")

        embed.add_field(name='Notification Sent to', value=f'{member.mention} - `{member.id}`')
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
        

def setup(bot: utils.Bot):
    bot.add_cog(Info(bot))