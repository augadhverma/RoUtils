import aiohttp
import traceback
import discord

from discord.ext import commands
from datetime import datetime

from .info import RobloxUserNotFound

class Handler(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot

    async def mystbin(self, data):
      data = bytes(data, 'utf-8')
      async with aiohttp.ClientSession() as cs:
        async with cs.post('https://mystb.in/documents', data = data) as r:
          res = await r.json()
          key = res["key"]
          return f"https://mystb.in/{key}"

    @commands.Cog.listener()
    async def on_command_error(self, ctx:commands.Context, error):
        """An error handler
        
        Parameters
        ------------
        ctx: commands.Context
            The context used for command invocation.
        error: commands.CommandError
            The Exception raised.
        """
    
        if hasattr(ctx.command, 'on_error'):
            return

        ignored = (
            commands.CommandNotFound
        )

        add_x = (
            commands.CheckFailure,
            commands.NotOwner,
            commands.MissingPermissions
        )

        handler = (
            commands.MissingRequiredArgument,
            commands.TooManyArguments
        )

        private = (
            commands.PrivateMessageOnly,
            commands.NoPrivateMessage
        )

        if isinstance(error, ignored):
            return

        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(f"I am missing the following permission(s): {error.missing_perms}")
            return
        
        elif isinstance(error, add_x):
            await ctx.message.add_reaction("<:x_:811230315648647188>")
            return

        elif isinstance(error, commands.BadUnionArgument):
            if isinstance(error.errors[1], commands.UserNotFound):
                await ctx.send(error.errors[1])
                return

        elif isinstance(error, (commands.MemberNotFound, commands.UserNotFound)):
            return await ctx.send(f'User "{error.argument}" not found')
        
        elif isinstance(error, commands.CommandInvokeError):
            if isinstance(error.__cause__, RobloxUserNotFound):
                return await ctx.send(error.original)
            else:
                return

        elif isinstance(error, private):
            await ctx.send(error.message)
            return

        elif isinstance(error, handler):
            await ctx.send_help(ctx.command)
            return

        else:
            tb ="".join(traceback.format_exception(type(error), error, error.__traceback__))
            try:
                embed = discord.Embed(
                    description = f"```py\n{tb}```",
                    colour=discord.Colour.red(),
                    title="An unexpected error occured",
                    timestamp=datetime.utcnow()
                )
                embed.set_footer(text=f"Caused by command: {ctx.command}")

                await ctx.send(embed=embed)
            except:
                err = await self.mystbin(tb)
                embed = discord.Embed(
                    title="An unexpected error occured",
                    timestamp=datetime.utcnow(),
                    colour=discord.Colour.red(),
                    description=f"The error is too long to send.\nHere, I have uploaded the error to [MystBin]({err}).",
                    url=err
                )
                embed.set_footer(text=f"Caused by command: {ctx.command}")
                await ctx.send(embed=embed)
            raise error


def setup(bot):
    bot.add_cog(Handler(bot))