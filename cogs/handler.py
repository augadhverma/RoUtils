"""
This Discord Bot has been made to keep the server of RoWifi safe and a better place for everyone

Copyright © 2020 ItsArtemiz (Augadh Verma). All rights reserved.

This Software is distributed with the GNU General Public License (version 3).
You are free to use this software, redistribute it and/or modify it under the
terms of GNU General Public License version 3 or later.

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of this Software.

This Software is provided AS IS but WITHOUT ANY WARRANTY, without the implied
warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

For more information on the License, check the LICENSE attached with this Software.
If the License is not attached, see https://www.gnu.org/licenses/
"""

import discord
from discord.ext import commands
from datetime import datetime

class ErrorHandler(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx:commands.Context, error):
        ignored = (
            commands.NotOwner,
            commands.CommandNotFound
        )
        handler = (
            commands.NoPrivateMessage,
            commands.PrivateMessageOnly,
            commands.BotMissingPermissions,
            commands.MissingRequiredArgument,
            commands.TooManyArguments
        )

        if isinstance(error, ignored):
            return
        elif isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                title = "Command On Cooldown",
                colour = discord.Colour.red(),
                description = f"`{ctx.command}` is on a cooldown. Retry after **{error.retry_after:.2f}s**.",
                timestamp = datetime.utcnow()
            )
            embed.set_footer(text=self.bot.footer)

            await ctx.send(embed=embed)
        elif isinstance(error, commands.CheckFailure):
            await ctx.message.delete()
        elif isinstance(error, handler):
            await ctx.send(content="Invalid command usage...")
            return await ctx.send_help(ctx.command)
        else:
            raise error

def setup(bot:commands.Bot):
    bot.add_cog(ErrorHandler(bot))