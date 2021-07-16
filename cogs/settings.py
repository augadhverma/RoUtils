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
from typing import Literal, Optional

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
            discord.Status.offline,
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