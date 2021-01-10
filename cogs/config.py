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
import os
import random

from discord.ext import commands, tasks
from datetime import datetime

class Config(commands.Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        self.change_presence.start()

    @commands.command()
    @commands.is_owner()
    async def load(self, ctx:commands.Context, name:str):
        """Loads an extension based on the name given.

        Args:
            name (str): The name of the cog.
        """
        try:
            self.bot.load_extension(f"cogs.{name}")
        except Exception as e:
            return await ctx.reply(f"```py\n{e}```")
        await ctx.reply(f"📥 Loaded extension: **`cogs/{name}.py`**.")


    @commands.command()
    @commands.is_owner()
    async def unload(self, ctx:commands.Context, name:str):
        """Unloads an extension based on the name given.

        Args:
            name (str): The name of the cog.
        """
        try:
            self.bot.unload_extension(f"cogs.{name}")
        except Exception as e:
            return await ctx.reply(f"```py\n{e}```")

        return await ctx.reply(f"📤 Unloaded extension: **`cogs/{name}.py`**.")

    @commands.command(name="reload")
    @commands.is_owner()
    async def _reload(self, ctx:commands.Context, name:str):
        """Reloads an extension based on the name given or reloads all the loaded cogs.

        Args:
            name (str): The name of the cog. Use `all` if you want to load all cogs.
        """
        if name.lower() == "all":
            for f in os.listdir("cogs"):
                if f.endswith(".py"):
                    name = f[:-3]
                    try:
                        self.bot.reload_extension(f"cogs.{name}")
                    except Exception as e:
                        await ctx.send(f"```\n{e}```")
            return await ctx.reply("🔄 Reloaded all extensions.")
        
        else:
            try:
                self.bot.reload_extension(f"cogs.{name}")
            except Exception as e:
                return await ctx.reply(f"```py\n{e}```")
            return await ctx.reply(f"🔄 Reloaded extension: **`cogs/{name}.py`**.")


    @commands.command()
    @commands.is_owner()
    async def cogs(self, ctx:commands.Context):
        """Displays all active cogs"""
        embed = discord.Embed(
            title="Active Cogs",
            description="\n".join([cog for cog in self.bot.cogs.keys()]),
            colour=self.bot.colour,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=self.bot.footer)

        await ctx.reply(embed=embed)

    @property
    async def get_activity(self) -> str:
        """Returns the playing status

        Returns:
            str
        """
        ch = [
            "with Mel",
            "RealLife.exe",
            "with life",
            "with RoWifi",
            "with RoWifi | Use .help"
        ]

        return random.choice(ch)

    @tasks.loop(minutes=5.0)
    async def change_presence(self):
        name = await self.get_activity

        await self.bot.change_presence(activity=discord.Game(name=name))

    @change_presence.before_loop
    async def before_change_presence(self):
        await self.bot.wait_until_ready()

    def cog_unload(self):
        self.change_presence.cancel()


def setup(bot:commands.Bot):
    bot.add_cog(Config(bot))