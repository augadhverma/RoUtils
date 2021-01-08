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

from discord.ext import commands

from dotenv import load_dotenv
load_dotenv()

intents = discord.Intents.all()

os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
os.environ["JISHAKU_HIDE"] = "True"

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("."),
    case_insensitive=True,
    intents=intents,
    allowed_mentions=discord.AllowedMentions(users=True, everyone=False, roles=False, replied_user=False)
)

bot.colour = 0x210070
bot.footer = "RoUtils"

@bot.event
async def on_ready():
    print("{0.user} is up and running".format(bot))

for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        bot.load_extension("cogs.{}".format(filename[:-3]))

bot.load_extension("jishaku")

bot.run(os.environ.get("BotToken"))