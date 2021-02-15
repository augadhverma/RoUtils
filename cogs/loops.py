from discord.ext import tasks, commands

class ClearCache(commands.Cog):
    def __init__(self, bot:commands.Bot) -> None:
        self.bot = bot
        self.clear_cache.start()

    def cog_unload(self):
        self.clear_cache.cancel()

    @tasks.loop(minutes=1.0)
    async def clear_cache(self):
        cogs = ("info", "tags")
        try:
            for cog in cogs:
                self.bot.reload_extension(f"cogs.{cog}")
        except:
            pass


    @clear_cache.before_loop
    async def before_clear_cache(self):
        await self.bot.wait_until_ready()



def setup(bot:commands.Bot):
    bot.add_cog(ClearCache(bot))