from collections import namedtuple
import discord
from discord.ext import commands

import os

TOKEN = "Nzk2MDU0MDg5MDgzNTE4OTk2.X_SVJA.TMpLMMUCwWO-A2fbt9GisAX4WbM"

# ----- some useful vars -----

prefix = {"/",";"}
mentions = discord.AllowedMentions(
    everyone=False, # disables pinging everyone
    roles=False, # disables pinging roles
    users=True, # enables pinging users
    replied_user=True # enable pinging replied user
)
intents = discord.Intents.all()

# ----- Defining bot -----

bot = commands.Bot(command_prefix=commands.when_mentioned_or(*prefix),allowed_mentions=mentions, case_insensitive=True, intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user} is now up and running.")

# ----- Bot Vars -----

bot.colour = discord.Colour.blurple()
bot.footer = "RoUtils"
bot.version = "1.0.0a"

VersionInfo = namedtuple("VersionInfo", "major minor micro releaselevel serial")
bot.version_info = VersionInfo(major=1, minor=0, micro=0, releaselevel='alpha', serial='0')

# ----- Jishaku Config -----
os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
os.environ["JISHAKU_HIDE"] = "True"

# ----- Loading Cogs -----

for f in os.listdir('./cogs'):
    if f.endswith('.py'):
        bot.load_extension(f"cogs.{f[:-3]}")

bot.load_extension("jishaku")

bot.run(TOKEN)