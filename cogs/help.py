"""
Replaces the old help command.

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

from unicodedata import decomposition
import discord

from discord.ext import commands
from datetime import datetime
from bot import RoUtils
from typing import Mapping, Union

class CustomHelp(commands.HelpCommand):
    def __init__(self, **options):
        try:
            self.colour = options['colour']
        except KeyError:
            self.colour = options.get('color', 0x2F3136)
        self.footer = options.get('footer', 'RoUtils')

        super().__init__(
            command_attrs = {
                'help':'Shows this help message.',
                'usage':'[command/category]'
            },
            **options
        )

    def command_usage(self, cmd:Union[commands.Command, commands.Group]) -> str:
        return f"{cmd.qualified_name} {cmd.signature}"

    def command_help(self, cmd:Union[commands.Command, commands.Group]) -> str:
        return cmd.help if cmd.help else 'No help provided...'

    async def send_bot_help(self, mapping:Mapping):
        embed = discord.Embed(
            colour = self.colour,
            title = 'Help',
            description = f'Type `{self.clean_prefix}help [command/category]` for more info on a command or a category.',
            timestamp = datetime.utcnow()
        )
        embed.set_footer(text=self.footer)

        for cog, cmds in mapping.items():
            if cog and cmds:
                f = await self.filter_commands(cmds, sort=True)
                if f:
                    try:
                        embed.add_field(
                            name = cog.qualified_name,
                            value = ', '.join([f'`{c.name}`' for c in f]),
                            inline = False
                        )
                    except:
                        pass

        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command:Union[commands.Command, commands.Group]):
        # Making one command for bot group and command help
        embed = discord.Embed(
            title = 'Help',
            description = self.command_help(command),
            colour = self.colour,
            timestamp = datetime.utcnow()
        )
        embed.set_footer(text=self.footer)

        embed.add_field(
            name = 'Usage',
            value = f'`{self.command_usage(command)}`',
            inline = False
        )

        if command.aliases:
            embed.add_field(
                name = 'Aliases',
                value = ', '.join([f'`{c}`' for c in command.aliases]),
                inline = False
            )

        if isinstance(command, commands.Group):
            f = await self.filter_commands(command.commands, sort=True)
            if f:
                embed.add_field(
                    name = 'Subcommands',
                    value = ', '.join([f'`{c.name}`' for c in f]),
                    inline = False
                )

        await self.get_destination().send(embed=embed)

    send_group_help = send_command_help

    async def send_cog_help(self, cog:commands.Cog):
        embed = discord.Embed(
            title = f'Category: {cog.qualified_name}',
            colour = self.colour,
            timestamp = datetime.utcnow()
        )

        embed.set_footer(text = self.footer)

        if cog.description:
            embed.description = cog.description

        f = await self.filter_commands(cog.get_commands(), sort=True)
        if f:
            embed.add_field(
                name = 'Commands:',
                value = ', '.join([f'`{c.name}`' for c in f]),
                inline = False
            )

        await self.get_destination().send(embed=embed)


class Help(commands.Cog):
    """ RoUtils' help command. """
    def __init__(self, bot:RoUtils):
        self.bot = bot
        self.bot._original_help_cmd = bot.help_command
        self.bot.help_command = CustomHelp(colour=self.bot.invisible_colour, footer=self.bot.footer)
        self.bot.help_command.cog = self

    def cog_unload(self):
        self.bot.help_command = self.bot._original_help_cmd


def setup(bot:RoUtils):
    bot.add_cog(Help(bot))