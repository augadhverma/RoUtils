"""
The main bot
Copyright (C) 2021-present ItsArtemiz (Augadh Verma)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

# version 3.1

import os
import aiohttp
import discord
import dotenv
import random
import logging
import sys

from typing import Literal, Optional, Union, Any
from discord.ext import commands

from .db import Client
from .context import Context
from .models import GuildSettings, Infraction, InfractionType

dotenv.load_dotenv()

URI = os.environ.get("URI") #mongodb uri
TOKEN = os.environ.get("TOKEN") #bot token

os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True" 
os.environ["JISHAKU_HIDE"] = "True"

# log formatter taken straight from discord module

def stream_supports_colour(stream: Any) -> bool:
    is_a_tty = hasattr(stream, 'isatty') and stream.isatty()
    if sys.platform != 'win32':
        return is_a_tty

    # ANSICON checks for things like ConEmu
    # WT_SESSION checks if this is Windows Terminal
    # VSCode built-in terminal supports colour too
    return is_a_tty and ('ANSICON' in os.environ or 'WT_SESSION' in os.environ or os.environ.get('TERM_PROGRAM') == 'vscode')


logger = logging.getLogger(__name__)
log_handler = logging.StreamHandler()

if stream_supports_colour(log_handler.stream):
    log_formatter = discord.utils._ColourFormatter()
else:
    dt_fmt = '%Y-%m-%d %H:%M:%S'
    log_formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')

log_handler.setFormatter(log_formatter)

logger.setLevel(logging.DEBUG)
logger.addHandler(log_handler)

async def prefix(bot, message: discord.Message):
    base = []
    if message.guild is None:
        base.append(".")
    
    else:
        settings: dict = await bot.settings.find_one({"_id":message.guild.id})
        if settings is None:
            base.append(".")
        else:
            base.append(settings.get('prefix', '.'))

    return commands.when_mentioned_or(*base)(bot, message)

class Bot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True

        super().__init__(
            command_prefix=prefix,
            strip_after_prefix=True,
            allowed_mentions=discord.AllowedMentions.none(),
            owner_id=449897807936225290,
            case_insensitive=True,
            intents=intents,
            enable_debug_evens=True,
        )

        self.initial_extensions = {
            "cogs.settings",
            "cogs.tags",
            "jishaku",
            "cogs.handler",
            "cogs.mod",
            "cogs.info",
            "cogs.discord_events"
        }

        self.colour = discord.Colour.blue()
    
    async def on_ready(self) -> None:
        print(f'Ready {self.user} (ID: {self.user.id})')

        if not hasattr(self, 'uptime'):
            self.uptime = discord.utils.utcnow()

    async def setup_hook(self) -> None:
        self.session = aiohttp.ClientSession()
        self.loop.create_task(self.create_sessions())
        for ext in self.initial_extensions:
            try:
                await self.load_extension(ext)
            except Exception as e:
                raise e
        self.footer = self.user.name
        
        
    async def close(self) -> None:
        await super().close()
        if hasattr(self, 'session'):
            await self.session.close()

    async def create_sessions(self) -> None:
        db = "Utilities"
        if not hasattr(self, 'tags'):
            self.tags = Client(URI, db, 'Tags')
        if not hasattr(self, 'infractions'):
            self.infractions = Client(URI, db, 'Infractions')
        if not hasattr(self, 'settings'):
            self.settings = Client(URI, db, 'Settings')
        if not hasattr(self, 'embeds'):
            self.embeds = Client(URI, db, 'Embeds')
        temp = [
            ("playing", "with ItsArtemiz"),
            ("playing", "with RoWifi"),
            ("competing", "Roblox"),
            ("listening", "song"),
            ("watching", "tickets")
        ]
        activity = random.choice(temp)
        await self.wait_until_ready()
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType[activity[0]], name=activity[1]))
        logger.info(f"Status Changed: {activity[0]} {activity[1]}")
        
    async def get_context(self, origin: Union[discord.Message, discord.Interaction], *, cls=None):
        return await super().get_context(origin, cls=Context)

    async def get_guild_settings(self, id: int, /) -> GuildSettings:
        document = await self.settings.find_one({'_id':id})
        if document:
            return GuildSettings(document)
        
        document = {
            '_id':id,
            'prefix':'.',
            'logChannels':{'bot':None, 'message':None},
            'extraRoles':{'admin':None, 'bypass':None},
            'modRoles':{'mod': None, 'senior mod':None},
            'commandDisabledChannels':[],
            'badWords':[],
            'domainsWhitelisted':[],
            'detectionExclusiveChannels':[],
            'muteRole':None,
            'domainDetection':False,
            'badWordDetection':False,
            'timeoutInsteadOfMute':False,
            'ticketsChannel':None
        }

        await self.settings.insert_one(document)
        return GuildSettings(document)

    async def get_infraction(self, id: int, guild_id: int, /) -> Optional[Infraction]:
        document = await self.infractions.find_one({'id':id, 'guild_id':guild_id})
        if document:
            return Infraction(document)
        return

    async def get_next_infraction_id(self) -> int:
        return (await self.infractions.count_documents({})) + 1

    async def insert_infraction(
        self,
        offender_id: int,
        moderator_id: int,
        reason: str,
        type: InfractionType,
        until: Optional[float],
        guild_id: int
    ) -> Infraction:
        pass

        document = {
            "id":await self.get_next_infraction_id(),
            "moderator":moderator_id,
            "offender":offender_id,
            "reason":reason,
            "type":type.value,
            "deleted":False,
            "until":until,
            "guild_id":guild_id
        }

        insert = await self.infractions.insert_one(document)
        document['_id'] = insert.inserted_id

        return Infraction(document)

    async def post_log(
        self,
        guild: discord.Guild,
        log_type: Literal['bot', 'message', 'infractions'],
        **kwargs
    ) -> Optional[discord.Message]:
        settings = await self.get_guild_settings(guild.id)

        channel_id = settings.log_channels.get(log_type) or settings.log_channels.get('bot')
        if channel_id is None:
            return
        channel = guild.get_channel(channel_id)
        if channel is None:
            try:
                channel = await guild.fetch_channel(channel_id)
            except:
                return

        return await channel.send(**kwargs)

    def run(self) -> None:
        super().run(token=TOKEN)