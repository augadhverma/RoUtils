from discord.ext import commands, tasks
from collections import namedtuple
from utils.checks import council
from typing import Optional

import os
import random
import discord

class Config(commands.Cog, description="Bot configuration related things."):
    def __init__(self, bot:commands.Bot) -> None:
        self.bot = bot
        self.bot_change_presence.start()

    def cog_unload(self):
        self.bot_change_presence.cancel()

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

    def get_activity(self) -> namedtuple:
        Activity = namedtuple("Activity", ["type","name"])
        activities = {
            "watching":"the city burn 🔥",
            "listening":"mom",
            "playing":"with RoWifi",
            "watching":"nzp, the noob king :D"
        }

        activity = random.choice(list(activities.keys()))
        return Activity(discord.ActivityType[activity], activities[activity])

    def get_status(self) -> discord.Status:
        return random.choice([
            discord.Status.online,
            discord.Status.dnd,
            discord.Status.idle
        ])

    @tasks.loop(minutes=5.0)
    async def bot_change_presence(self) -> None:
        activity = self.get_activity()
        status = self.get_status()

        await self.bot.change_presence(
            activity=discord.Activity(
                type=activity.type,
                name=activity.name
            ),
            status = status
        )

    @bot_change_presence.before_loop
    async def before_change_presence(self) -> None:
        await self.bot.wait_until_ready()


    @council()
    @commands.group(name="status", invoke_without_command=True)
    async def change_status(self, ctx:commands.Context, type:str, *, status:str):
        """Changes the bot status."""
        member:discord.Member = ctx.guild.get_member(self.bot.user.id)
        if not type.lower() in ("playing","watching","listening","competing"):
            type = "playing"

        self.bot_change_presence.cancel()
        await self.bot.change_presence(
            activity=discord.Activity(
            type=discord.ActivityType[type],
            name=status
        ),
        status=member.status
        )

        await ctx.send("\U0001f44c")

    @council()
    @change_status.command(name="type")
    async def _type(self, ctx:commands.Context, activity:Optional[str]):
        """Changes bot activity state."""
        activity = activity or "online"
        member:discord.Member = ctx.guild.get_member(self.bot.user.id)

        await self.bot.change_presence(status=discord.Status[activity], activity=member.activity)
        await ctx.send("\U0001f44c")

    @council()
    @change_status.command()
    async def resume(self, ctx:commands.Context):
        """Resumes the bot looping status."""
        try:
            self.bot_change_presence.start()
        except RuntimeError:
            pass
        await ctx.send("\U0001f44c")


def setup(bot:commands.Bot):
    bot.add_cog(Config(bot))        