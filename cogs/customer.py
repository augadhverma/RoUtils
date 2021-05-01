import discord
import time
from discord.ext import tasks, commands
from typing import Optional, Union

from utils.requests import get, HTTPException
from utils.checks import bot_channel, council

RoWifiHQ = 576325772629901312
CustomerRole = 581428516269064203
TestRole = 711822976160497674
TestServer = 702180216533155933

class Customer(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot


def setup(bot:commands.Bot):
    bot.add_cog(Customer(bot))
