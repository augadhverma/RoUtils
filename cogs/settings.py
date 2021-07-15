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

from discord.ext import commands
from typing import Optional

class Settings(commands.Cog):
    def __init__(self, bot: utils.Bot) -> None:
        self.bot = bot

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

    @settings.command(aliases=['command'])
    async def commands(self, ctx: utils.Context, channel: Optional[discord.TextChannel], *, option: str):
        """Enables or Disables commands in a channel.
        
        Enable using: `enable` or `on`
        Disable using: `disable` or `off`
        """
        channel = channel or ctx.channel
        settings = await self.bot.utils.find_one({'type':'settings'})
        channels = settings.get('disabledChannels', [])
        
        prefixes = [self.bot.user.mention]
        prefixes.extend(settings.get('prefixes', ['.']))

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

def setup(bot: utils.Bot):
    bot.add_cog(Settings(bot))