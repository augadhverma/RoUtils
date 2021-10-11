"""
The Settings module - for bot settings.
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
import utils
import random

from discord.ext import commands, tasks
from typing import List, Literal, Optional
from jishaku.paginators import PaginatorEmbedInterface

class Settings(commands.Cog):
    def __init__(self, bot: utils.Bot) -> None:
        self.bot = bot
        self.changing_status.start()

    def cog_check(self, ctx: utils.Context):
        return ctx.guild and ctx.author.guild_permissions.administrator == True

    @commands.group(invoke_without_command=True)
    async def settings(self, ctx: utils.Context):
        """Shows bot settings."""
        settings = await self.bot.utils.find_one({'type':'settings'})
        
        log = settings.get('log', None)
        disabledChannels = settings.get('disabledChannels', [])
        ticket = settings.get('ticket', 'None set')
        prefixes = [self.bot.user.mention]
        prefixes.extend(settings.get('prefixes', ['.']))

        if self.bot.version_info.releaselevel != 'final':
            prefixes.extend(['b.', 'b!'])
                
        embed = discord.Embed(title='Settings', colour=ctx.colour, timestamp=utils.utcnow())
        embed.set_footer(text=ctx.footer)
        
        channel = 'None set'
        disabled = 'None disabled'

        if log:
            channel = f'<#{log}>'

        if disabledChannels:
            disabled = '\n'.join(f'{i}. <#{c}>' for i, c in enumerate(disabledChannels, 1))

        embed.add_field(name='Log Channel', value=channel)
        embed.add_field(name='Blacklisted Channels', value=disabled)
        embed.add_field(name='Prefixes', value='\n'.join(f'{i}. {p}' for i,p in enumerate(prefixes, 1)))
        embed.add_field(name='Mute Role', value=f'<@&{settings["muteRole"]}>')
        embed.add_field(name='Ticket Category', value=f'<#{ticket}>' if isinstance(ticket, int) else ticket)

        await ctx.reply(embed=embed)

    @settings.command(name='commands', aliases=['command'])
    async def cmds(self, ctx: utils.Context, channel: Optional[discord.TextChannel], *, option: str):
        """Enables or Disables commands in a channel.
        
        Enable using: `enable` or `on`
        Disable using: `disable` or `off`
        """
        channel = channel or ctx.channel
        settings = await self.bot.utils.find_one({'type':'settings'})
        channels = settings.get('disabledChannels', [])
        

        if option in ('disable', 'off'):
            channels.append(channel.id)
            update = 'disabled'
        elif option in ('enable', 'on'):
            channels.remove(channel.id)
            update = 'enabled'
        else:
            return await ctx.send('Invalid option given.')

        await self.bot.utils.update_one(
            {'type':'settings'},
            {'$set':{'disabledChannels':list(set(channels))}}
        )

        await ctx.tick(True)
        await ctx.send(f'Commands succesfully **{update}** for `#{channel.name}`!')

    @settings.group(invoke_without_command=True)
    async def prefix(self, ctx: utils.Context):
        """Shows all set prefixes."""
        settings = await self.bot.utils.find_one({'type':'settings'})
        prefixes = [self.bot.user.mention]
        prefixes.extend(settings.get('prefixes', ['.']))

        if self.bot.version_info.releaselevel != 'final':
            prefixes.extend(['b.', 'b!'])

        embed = discord.Embed(
            title='All Prefixes',
            description='\n'.join(f'{i}. {p}' for i,p in enumerate(prefixes, 1)),
            timestamp=utils.utcnow(),
            colour=ctx.colour
        )

        embed.set_footer(text=ctx.footer)

        await ctx.reply(embed=embed)

    @prefix.command(name='add')
    async def _add(self, ctx: utils.Context, *, prefix: str):
        """Adds a prefix"""
        settings = await self.bot.utils.find_one({'type':'settings'})
        prefixes: list[str] = settings.get('prefixes')
        prefixes.append(prefix)
        prefixes = list(set(prefixes))

        await self.bot.utils.update_one(
            {'type':'settings'},
            {'$set':{'prefixes':prefixes}}
        )

        await ctx.tick(True)

    @prefix.command()
    async def remove(self, ctx: utils.Context, *, prefix: str):
        """Adds a prefix"""
        settings = await self.bot.utils.find_one({'type':'settings'})
        prefixes: list[str] = settings.get('prefixes')
        try:
            prefixes.remove(prefix)
        except:
            pass
        prefixes = list(set(prefixes))

        await self.bot.utils.update_one(
            {'type':'settings'},
            {'$set':{'prefixes':prefixes}}
        )

        await ctx.tick(True)

    @settings.command(aliases=['mr', 'muted-role'])
    async def muterole(self, ctx: utils.Context, *, role: Optional[discord.Role]):
        """Sets or displays the muted role."""
        settings = await self.bot.utils.find_one({'type':'settings'})
        
        if role:
            await self.bot.utils.update_one({'type':'settings'}, {'$set':{'muteRole':role.id}})
            await ctx.tick(True)
        elif role is None:
            role: discord.Role = ctx.guild.get_role(settings['muteRole'])
            await ctx.send(f'Role: {role.mention} (ID: {role.id})\nMembers Muted: {len(role.members)}')

    @settings.command()
    async def log(self, ctx: utils.Context, *, channel: Optional[discord.TextChannel]):
        """Sets or displays the log channel for the server"""
        settings = await self.bot.utils.find_one({'type':'settings'})
        if channel:
            await self.bot.utils.update_one({'type':'settings'}, {'$set':{'log':channel.id}})
            await ctx.tick(True)
        elif channel is None:
            await ctx.send(f'Current log channel is <#{settings["log"]}>')

    @settings.command()
    async def ticket(self, ctx: utils.Context, *, channel: Optional[discord.CategoryChannel]):
        """Sets a category as the ticket category so tickets can be opened there."""
        settings = await self.bot.utils.find_one({'type':'settings'})
        if channel:
            await self.bot.utils.update_one({'type':'settings'}, {'$set':{'ticket':channel.id}}, upsert=True)
            await ctx.tick(True)
        elif channel is None:
            await ctx.send(f'Current Ticket Category is <#{settings.get("ticket")}>')

    @settings.group(aliases=['badwords'], invoke_without_command=True)
    async def badword(self, ctx: utils.Context):
        """Shows all bad words set."""

        embed = discord.Embed(
            title = 'All Bad Words Registered',
            colour = discord.Colour.blue(),
            timestamp = utils.utcnow()
        )

        settings = await self.bot.utils.find_one({'type':'settings'})
        words: List[str] = settings.get('badWords', [])

        paginator = commands.Paginator(prefix=None, suffix=None, max_size=500)
        for i, w in enumerate(words, 1):
            paginator.add_line(f'{i}. {w}')

        interface = PaginatorEmbedInterface(self.bot, paginator, owner=ctx.author, embed=embed)
        try:
            await interface.send_to(ctx)
        except Exception as e:
            await ctx.send(e)

    @badword.command(name='add')
    async def add_badword(self, ctx: utils.Context, *, word: str):
        """Adds a bad word to the database."""
        settings = await self.bot.utils.find_one({'type':'settings'})

        words: List[str] = settings.get('badWords', [])
        for w in word.split():
            words.append(w)
        words = list(set(words))
        await self.bot.utils.update_one({'type':'settings'}, {'$set':{'badWords':words}})
        await ctx.tick(True)

    @badword.command(name='remove')
    async def remove_badword(self, ctx: utils.Context, *, word: str):
        """Removes a word from the database."""
        settings = await self.bot.utils.find_one({'type':'settings'})
        words: List[str] = settings['badWords']
        try:
            words.remove(word)
            await self.bot.utils.update_one({'type':'settings'}, {'$set':{'badWords':words}})
        except ValueError:
            pass
        finally:
            await ctx.tick(True)

    @settings.group(name='domain', aliases=['links', 'link'], invoke_without_command=True)
    async def link(self, ctx: utils.Context):
        """Shows all links that are whitelisted."""

        embed = discord.Embed(
            title = 'All Whitelisted links',
            colour = discord.Colour.blue(),
            timestamp = utils.utcnow()
        )

        settings = await self.bot.utils.find_one({'type':'settings'})
        words: List[str] = settings.get('linkWhitelist', [])

        paginator = commands.Paginator(prefix=None, suffix=None, max_size=500)
        for i, w in enumerate(words, 1):
            paginator.add_line(f'{i}. {w}')

        interface = PaginatorEmbedInterface(self.bot, paginator, owner=ctx.author, embed=embed)
        try:
            await interface.send_to(ctx)
        except Exception as e:
            await ctx.send(e)
            raise e

    @link.command(name='add')
    async def add_link(self, ctx: utils.Context, domain: str):
        """Adds a domain to be whitelisted"""

        settings = await self.bot.utils.find_one({'type':'settings'})

        links: List[str] = settings.get('linkWhitelist', [])
        links.append(domain)
        links = list(set(links))
        await self.bot.utils.update_one({'type':'settings'}, {'$set':{'linkWhitelist':links}})
        await ctx.tick(True)

    @link.command(name='remove')
    async def remove_link(self, ctx: utils.Context, domain: str):
        """Removes a word from the database."""
        settings = await self.bot.utils.find_one({'type':'settings'})
        words: List[str] = settings['linkWhitelist']
        try:
            words.remove(domain)
            await self.bot.utils.update_one({'type':'settings'}, {'$set':{'linkWhitelist':words}})
        except ValueError:
            pass
        finally:
            await ctx.tick(True)


    @commands.command()
    async def status(self, ctx: utils.Context, *, option: str):
        """Sets the bot's status"""
        options = ('online', 'dnd', 'idle')
        if option.casefold() not in options:
            return await ctx.send('Invalid option provided. Please provide either of the options: '+', '.join(f'`{o}`' for o in options))

        await self.bot.change_presence(
            activity=ctx.me.activity,
            status=discord.Status[option]
        )

        await ctx.tick(True)

    @commands.group(invoke_without_command=True, aliases=['activities'])
    async def activity(self, ctx: utils.Context):
        """Lists the activities of the bot."""
        activities_dict = await self.bot.utils.find_one({'type':'activities'})
        activities: list[list[str, str]] = activities_dict['activities']

        embed = discord.Embed(
            title='Status List',
            colour=ctx.colour,
            timestamp=utils.utcnow()
        )


        description = ''
        for i, L in enumerate(activities, 1):
            if L[0] == 'competing':
                L[0] = 'competing in'

            description+=f'{i}. `{L[0].capitalize()} {L[1]}`\n'

        embed.description = description

        await ctx.reply(embed=embed)


    @activity.command(name='add')
    async def add_activity(self, ctx: utils.Context, option: str, *, text: str):
        """Adds an activity"""
        option = option.casefold()
        options = ('playing', 'listening', 'watching', 'competing')

        if option not in options:
            return await ctx.send('Invalid option provided. Please provide either of the options: '+', '.join(f'`{o}`' for o in options))

        activity_dict = await self.bot.utils.find_one({'type':'activities'})
        activities: list[list[str, str]] = activity_dict['activities']

        for activity in activities:
            if activity == [option, text]:
                return await ctx.send(f'The given activity `{option.capitalize()} {text}` is already registered with me.')
        else:
            activities.append([option, text])
            await self.bot.utils.update_one(
                {'type':'activities'},
                {'$set':{'activities':activities}}
            )

        await ctx.tick(True)

    @activity.command(name='remove')
    async def remove_activity(self, ctx: utils.Context, option: str, *, text:str):
        """Removes an activity. The text is case sensitive."""
        option = option.casefold()

        activity_dict = await self.bot.utils.find_one({'type':'activities'})
        activities: list[list[str, str]] = activity_dict['activities']

        for a in activities:
            if a == [option, text]:
                activities.remove([option, text])
                d = await self.bot.utils.update_one(
                    {'type':'activities'},
                    {'$set':{'activities':activities}}
                )
                return await ctx.tick(True)
        
        await ctx.reply(f'Could not find the activity `{option.capitalize()} {text}`')
        await ctx.tick(False)

    @activity.command(name='set')
    async def set_activity(self, ctx: utils.Context, option: str, *, text: str):
        """Sets an activity currently."""
        option = option.casefold()
        options = ('playing', 'listening', 'watching', 'competing')

        if option not in options:
            return await ctx.send('Invalid option provided. Please provide either of the options: '+', '.join(f'`{o}`' for o in options))

        await self.bot.change_presence(
            status=ctx.me.status,
            activity=discord.Activity(
                type=discord.ActivityType[option],
                name=text
            )
        )
        
        await ctx.tick(True)

    @activity.command(name='list')
    async def list_activity(self, ctx: utils.Context):
        """Lists all activities"""
        await ctx.invoke(self.activity)

    @tasks.loop(minutes=5.0)
    async def changing_status(self) -> None:
        status = random.choice([
            discord.Status.online,
            discord.Status.idle,
            discord.Status.dnd
        ])

        activity_dict = await self.bot.utils.find_one({'type':'activities'})
        activities: list[list[str, str]] = activity_dict['activities']

        activity = random.choice(activities)

        await self.bot.change_presence(
            status=status,
            activity=discord.Activity(
                type=discord.ActivityType[activity[0]],
                name=activity[1]
            )
        )

    @changing_status.before_loop
    async def before_change(self) -> None:
        await self.bot.wait_until_ready()

    @commands.command(name='loop', hidden=True)
    async def loop_run_cancel(self, ctx: utils.Context, *, option:Optional[Literal['start', 'stop']]):
        """Starts or stops the status loop."""
        is_running = self.changing_status.is_running()
        if option is None:
            return await ctx.reply(f'The status loop is currently {"running" if is_running else "not running"}')

        if option == 'start':
            if is_running:
                return await ctx.reply('The task is already running.')
            else:
                self.changing_status.start()
                await ctx.tick(True)
        elif option == 'stop':
            if is_running:
                self.changing_status.cancel()
                await ctx.tick(True)
            else:
                return await ctx.reply('The task is already stopped.')

    @loop_run_cancel.error
    async def error_on_loop(self, ctx: utils.Context, error: commands.CommandError):
        error = getattr(error, 'original', error)
        if isinstance(error, commands.BadLiteralArgument):
            return await ctx.send('Invalid option provided. Valid options are: `start`, `stop`.')
        else:
            raise error
    


def setup(bot: utils.Bot):
    bot.add_cog(Settings(bot))