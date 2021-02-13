from discord.ext import commands

import os

class Config(commands.Cog, description="Bot configuration related things."):
    def __init__(self, bot:commands.Bot) -> None:
        self.bot = bot

    @commands.is_owner()
    @commands.command(name="reload")
    async def _reload(self, ctx:commands.Context, *,name:str):
        """Reloads a cog."""

        if name == "all":
            for f in os.listdir("cogs"):
                if f.endswith(".py"):
                    name = f[:-3]
                    try:
                        self.bot.reload_extension(f"cogs.{name}")
                    except Exception as e:
                        return await ctx.send(f"```py\n{e}```")
            await ctx.reply("🔁 Reloaded all extensions.")
        else:
            try:
                self.bot.reload_extension(f"cogs.{name}")
            except Exception as e:
                return await ctx.send(f"```py\n{e}```")
            await ctx.reply(f"🔁 Reloaded extension: **`cogs/{name}.py`**")

    @commands.is_owner()
    @commands.command()
    async def load(self, ctx:commands.Context, *,name:str):
        """Loads a cog."""
        try:
            self.bot.load_extension(f"cogs.{name}")
        except Exception as e:
            return await ctx.send(f"```py\n{e}```")
        await ctx.send(f"📥 Loaded extension: **`cogs/{name}.py`**")

    @commands.is_owner()
    @commands.command()
    async def unload(self, ctx:commands.Context, *,name:str):
        """Unloads a cog."""
        try:
            self.bot.unload_extension(f"cogs.{name}")
        except Exception as e:
            return await ctx.send(f"```py\n{e}```")
        await ctx.send(f"📤 Unloaded extension: **`cogs/{name}.py`**")

def setup(bot:commands.Bot):
    bot.add_cog(Config(bot))        