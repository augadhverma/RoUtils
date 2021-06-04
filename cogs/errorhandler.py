"""
Handles Command Errors.

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

import discord
import sys
import traceback

from utils.logging import embed_builder, post_log
from utils.checks import NotBotChannel, NotAdmin, NotStaff
from utils.utils import TagNotFound
from discord.ext import commands
from bot import RoUtils

class CommandErrorHandler(commands.Cog):
    def __init__(self, bot:RoUtils):
        self.bot = bot

    async def mystbin(self, data) -> str:
        data = bytes(data, 'utf-8')
        r = await self.bot.session.post('https://mystb.in/documents', data=data)
        res = await r.json()
        key = res['key']
        return f'https://mystb.in/{key}.python'

    @commands.Cog.listener()
    async def on_command_error(self, ctx:commands.Context, error:commands.CommandError):
        """This event is triggered when an error is raised while invoking a command.

        Parameters
        ----------
        ctx : commands.Context
            The context used for command invocation.
        error : commands.CommandError
            The Exception raised.
        """

        if hasattr(ctx.command, 'on_error'):
            return

        ignored = (commands.CommandNotFound,)

        error = getattr(error, 'original', error)

        if isinstance(error, ignored):
            return

        if isinstance(error, commands.MissingPermissions):
            embed = embed_builder(
                bot=self.bot,
                title = "Missing Permissions <:pikawhat:820783879446855770>",
                description=str(error),
                user = ctx.author,
                colour = discord.Colour.red()
            )

            await ctx.send(embed=embed)

        elif isinstance(error, commands.BotMissingPermissions):
            embed = embed_builder(
                bot = self.bot,
                title = "I am missing some permissions <:notlikeblob:820784975577743390>",
                description=str(error),
                user = self.bot.user
            )

            try:
                await ctx.send(embed=embed)
            except:
                await ctx.send(str(error))

        elif isinstance(error, commands.CommandOnCooldown):
            embed = embed_builder(
                bot = self.bot,
                title=f"Command `{ctx.command}` is on cooldown <:blobStop:820783876556849192>",
                description = str(error),
                user = ctx.author
            )

            await ctx.send(embed = embed)

        elif isinstance(error, commands.NotOwner):
            embed = embed_builder(
                bot = self.bot,
                title = f"Command `{ctx.command}` is owner only",
                description=str(error),
                user = ctx.author
            )

            await ctx.send(embed=embed)

        elif isinstance(error, (commands.MemberNotFound, commands.UserNotFound)):
            embed = embed_builder(
                bot = self.bot,
                title = "Unable to locate the user <:notlikeblob:820784975577743390>",
                description = str(error),
                user = ctx.author
            )

            await ctx.send(embed=embed)

        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Invalid command usage, follow the help:")
            await ctx.send_help(ctx.command)
        
        elif isinstance(error, (NotStaff, NotAdmin, NotBotChannel, TagNotFound, commands.RoleNotFound)):
            await ctx.send(discord.utils.escape_mentions(str(error)))

        else:
            exception = "".join(traceback.format_exception(type(error), error, error.__traceback__))
            
            embed = embed_builder(
                bot = self.bot,
                title = "An Unexpected Error Occurred",
                description=str(error),
                user=ctx.author,
                colour= discord.Colour.red(),
                footer=f"Caused by: {ctx.command}"
            )
            
            embed.add_field(name="Full Error", value=await self.mystbin(exception))
            
            await ctx.send(embed = embed)
            
            await post_log(ctx.guild, name="bot-logs", embed=embed)

            print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
            print(exception)

def setup(bot:RoUtils):
    bot.add_cog(CommandErrorHandler(bot))