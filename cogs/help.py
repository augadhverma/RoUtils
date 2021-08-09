"""
Help Command Module - The bot's help command.
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

from typing import List, Mapping, Optional, Union
from discord.ext import commands
from utils import Bot, Context, utcnow

class HelpCmd(commands.HelpCommand):
    context: Context

    def __init__(self, **options):
        show_hidden: bool = options.pop('show_hidden', False)
        verify_checks: bool = options.pop('verify_checks', True)

        command_attrs = {
            'help':'Shows this message',
            'usage':'[command]'
        }
        
        super().__init__(show_hidden=show_hidden, verify_checks=verify_checks, command_attrs=command_attrs, **options)

    def get_command_signature(self, ctx: Context, command):
        if ctx is None or not ctx.valid:
            clean_prefix = ''
        else:
            clean_prefix = ctx.clean_prefix
        cmd = command
        return f'`{clean_prefix}{cmd.qualified_name} {cmd.signature}`'

    def get_command_help(self, command: Union[commands.Command, commands.Group]):
        return command.help or 'No help provided...'

    async def send_bot_help(self, mapping: Mapping[Optional[commands.Cog], List[commands.Command]]):
        embed = discord.Embed(
            colour=self.context.colour,
            title='Help',
            description=f'Type `{self.context.clean_prefix}help [command]` for more information on a command.',
            timestamp=utcnow()
        )

        for cog, cmds in mapping.items():
            if cog and cmds:
                filtered = await self.filter_commands(cmds, sort=True)
                if filtered:
                    try:
                        embed.add_field(
                            name=cog.qualified_name,
                            value=', '.join(f'`{c.name}`' for c in filtered),
                            inline=False
                        )
                    except:
                        pass
        
        await self.context.send(embed=embed)

    async def send_command_help(self, command: Union[commands.Command, commands.Group]):
        embed = discord.Embed(
            title=f'Help',
            description=self.get_command_help(command),
            colour=self.context.colour,
            timestamp=utcnow()
        )

        try:
            can_run = await command.can_run(self.context)
        except:
            can_run = False

        if can_run:
            text='You can run this command'
        else:
            text='You cannot run this command'

        embed.set_footer(text=text)

        embed.add_field(
            name='Usage',
            value=self.get_command_signature(self.context, command),
            inline=False
        )

        if command.aliases:
            embed.add_field(
                name='Aliases',
                value=', '.join(f'`{c}`' for c in command.aliases),
                inline=False
            )

        if isinstance(command, commands.Group):
            filtered = await self.filter_commands(command.commands)
            if filtered:
                embed.add_field(
                    name='Subcommands',
                    value=', '.join(f'`{c.name}`' for c in filtered),
                    inline=False
                )

        await self.context.send(embed=embed)

    send_group_help = send_command_help

class BotHelp(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.bot._original_help_cmd = bot.help_command
        self.bot.help_command = HelpCmd()

    def cog_unload(self):
        self.bot.help_command = self.bot._original_help_cmd

def setup(bot: Bot):
    bot.add_cog(BotHelp(bot))