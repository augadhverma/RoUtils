
import sys
import traceback
import aiohttp
import discord
import os

from discord.ext import commands
from dotenv import load_dotenv
from .db import Client

load_dotenv()

URI = os.environ.get('DB_TOKEN')
TOKEN = os.environ.get('BOT_TOKEN')

os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True" 
os.environ["JISHAKU_HIDE"] = "True"

initial_extensions = {
    'jishaku',
}

class Bot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True

        super().__init__(
            command_prefix=commands.when_mentioned_or('.', ';'),
            strip_after_prefix=True,
            allowed_mentions=discord.AllowedMentions.none(),
            owner_id=449897807936225290,
            case_insensitive=True,
            intents=intents
        )

        self.loop.create_task(self.create_session())

        self.version = '2.0.0b'
        
        for cog in initial_extensions:
            try:
                self.load_extension(cog)
            except Exception:
                print(f'Failed to load extension {cog}', file=sys.stderr)
                traceback.print_exc()

    async def create_session(self) -> None:
        db = 'Utilities'
        if not hasattr(self, 'session'):
            self.session = aiohttp.ClientSession(loop=self.loop)
        if not hasattr(self, 'tags'):
            self.tags = Client(URI, db, 'Tags')
        if not hasattr(self, 'infractions'):
            self.infractions = Client(URI, db, 'Infractions')
        if not hasattr(self, 'utils'):
            self.utils = Client(URI, db, 'Utils')
            
    async def on_ready(self) -> None:
        print(f'Ready {self.user} (ID: {self.user.id})')

    async def close(self):
        await super().close()
        await self.session.close()

    def run(self):
        return super().run(TOKEN, reconnect=True)