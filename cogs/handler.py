"""
The settings module.
Copyright (C) 2021-present ItsArtemiz (Augadh Verma)

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

import traceback
import discord
import logging

from discord.ext import commands
from utils import Bot, Context, ReasonError, HTTPException, CannotUseBotCommand, TagNotFound
from discord.app_commands import (
    AppCommandError,
    NoPrivateMessage,
    MissingPermissions,
    BotMissingPermissions,
    CheckFailure
)

logger = logging.getLogger('discord')

def signature(ctx: Context):
    if not ctx.valid:
        return 'N/A'
    cmd = ctx.command
    return f'{ctx.clean_prefix}{cmd.qualified_name} {cmd.signature}'

class Handler(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

        bot.tree.on_error = self.on_app_command_error

    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: AppCommandError
    ) -> None:

        send_original = (
            NoPrivateMessage,
            MissingPermissions,
            BotMissingPermissions,
            ReasonError,
            HTTPException,
            CannotUseBotCommand,
            TagNotFound
        )

        if isinstance(error, send_original):
            await interaction.response.send_message(str(error), ephemeral=True)
        elif isinstance(error, CheckFailure):
            await interaction.response.send_message("You probably don't have enough permissions to run this command.", ephemeral=True)
            
            logger.info(f"{interaction.user} ran {interaction.command.qualified_name} in {interaction.guild} and raised CheckFailure:\n{error.args}")
        else:
            error_type = type(error)
            trace = error.__traceback__
            lines = traceback.format_exception(error_type, error, trace)
            text = f'Command: {interaction.command.qualified_name}\n' + ''.join(lines)
            
            logger.error(text)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: Context, error: commands.CommandError) -> None:
        if hasattr(ctx.command, 'on_error'):
            return

        ignored = (commands.CommandNotFound, )

        error = getattr(error, 'original', error)

        cog: commands.Cog = ctx.cog
        if cog:
            if cog._get_overridden_method(cog.cog_command_error) is not None:
                return  

        if isinstance(error, ignored):
            return

        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.reply(f'You forgot to provide the `{error.param.name}` argument while using the command. Refer `{signature(ctx)}`?')

        elif isinstance(error, (commands.UserNotFound, commands.MemberNotFound)):
            return await ctx.reply(f'Could not find the user `{error.argument}`. Try again?')

        elif isinstance(error, commands.TooManyArguments):
            return await ctx.send(str(error))

        elif isinstance(error, commands.RoleNotFound):
            return await ctx.reply(f'Could not find the role `{error.argument}`. Try again?')
        
        elif isinstance(error, commands.CheckFailure):
            return await ctx.reply(f'You probably do not have enough permissions to use `{ctx.command.qualified_name}` command.')

        elif isinstance(error, AttributeError) and ctx.guild is None:
            return await ctx.reply(f'Cannot use `{ctx.command.qualified_name}` command in DMs')

        elif isinstance(error, commands.BadArgument):
            return await ctx.send(str(error))

        elif isinstance(error, discord.Forbidden):
            return await ctx.send(f'That action is forbidden. Maybe you are missing permissions?\nDiscord-side message: {str(error)}')

        elif isinstance(error, HTTPException):
            return await ctx.send(str(error))
        else:
            await ctx.send("An unkown error has occured", ephemeral=True)
            error_type = type(error)
            trace = error.__traceback__
            lines = traceback.format_exception(error_type, error, trace)
            text = __name__ + ''.join(lines)            
            logger.error(text)

async def setup(bot: Bot) -> None:
    await bot.add_cog(Handler(bot))