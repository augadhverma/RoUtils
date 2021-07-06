import aiohttp
import discord

from discord.ext import commands

class Context(commands.Context):

    def __init__(self, **attrs):
        super().__init__(**attrs)

    def __repr__(self) -> str:
        return '<Context>'

    @property
    def session(self) -> aiohttp.ClientSession:
        return self.bot.session

    @property
    def version(self) -> str:
        return self.bot.version

    @discord.utils.copy_doc(discord.Message.reply)
    async def reply(self, content, *, mention=True, **kwargs):
        msg: discord.Message = self.message

        default_mentions = discord.AllowedMentions.none()

        allowed_mentions = kwargs.pop('allowed_mentions', default_mentions)
        mention_author = kwargs.pop('mention_author', True)

        return await msg.reply(
            content=content, 
            allowed_mentions=allowed_mentions,
            mention_author=mention_author,
            **kwargs
        )