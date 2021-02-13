import discord

from typing import Union
from discord.ext import commands

from utils.cache import CacheType, Cache
from utils.classes import DiscordMember, DiscordUser, RobloxUser

class Information(commands.Cog, description="Info related stuff."):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        self.cache = Cache()

    @commands.command(aliases=['ui'])
    async def userinfo(self, ctx:commands.Context, *, user:Union[discord.Member, discord.User]=None):
        """Shows discord related info about a user"""
        user = user or ctx.author
        if isinstance(user, discord.Member):
            user = self.cache.get(CacheType.DiscordMember, user.id)
            if not user:
                expanded = DiscordMember()
                self.cache.set(CacheType.DiscordMember, user.id)




def setup(bot:commands.Bot):
    bot.add_cog(Information(bot))