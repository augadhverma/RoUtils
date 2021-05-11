"""
Bot configuration related.

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

from discord.ext import commands
from bot import RoUtils, extensions

class Config(commands.Cog):
    def __init__(self, bot:RoUtils) -> None:
        self.bot = bot

    @commands.is_owner()
    @commands.command()
    async def reload(self, ctx:commands.Cog, *,name:str):
        """ reloads a/all file(s). """
        if name == '~':
            for f in extensions:
                try:
                    self.bot.reload_extension(f)
                except Exception as e:
                    await ctx.send('```py\n{e}```')
            return await ctx.reply('Reloaded extensions.')

        else:
            try:
                self.bot.reload_extension(f"{name}")
            except Exception as e:
                return await ctx.send(f"```py\n{e}```")
            await ctx.reply(f"Successfully reloaded: **`{name.replace('.','/')}.py`**")

    @commands.is_owner()
    @commands.command()
    async def load(self, ctx:commands.Context, *,name:str):
        """Loads a cog."""
        try:
            self.bot.load_extension(f"{name}")
        except Exception as e:
            return await ctx.send(f"```py\n{e}```")
        await ctx.send(f"📥 Loaded extension: **`{name.replace('.','/')}.py`**")

    @commands.is_owner()
    @commands.command()
    async def unload(self, ctx:commands.Context, *,name:str):
        """Unloads a cog."""
        try:
            self.bot.unload_extension(f"{name}")
        except Exception as e:
            return await ctx.send(f"```py\n{e}```")
        await ctx.send(f"📤 Unloaded extension: **`{name.replace('.','/')}.py`**")

    # Add status loop


def setup(bot:RoUtils):
    bot.add_cog(Config(bot))