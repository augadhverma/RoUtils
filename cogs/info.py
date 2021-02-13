import discord

from typing import Union
from discord.ext import commands
from datetime import datetime

from utils.cache import Cache, CacheType
from utils.classes import RobloxUser
from utils.requests import get
from utils.errors import RobloxUserNotFound

class Requests:
    async def roblox_info(self, user:int) -> RobloxUser:
        try:
            roblox_id = (await get(f"https://api.rowifi.link/v1/users/{user}"))['roblox_id']
        except KeyError:
            raise RobloxUserNotFound("The user is not verified with RoWifi, please ask them to verify themselves by using `!verify`")
        info = await get(f"https://users.roblox.com/v1/users/{roblox_id}")
        return RobloxUser(info, user)

class Information(commands.Cog, description="Info related stuff."):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        self.cache = Cache()
        self.requests = Requests()


    @commands.command(aliases=['ui'])
    async def userinfo(self, ctx:commands.Context, *, user:Union[discord.Member, discord.User]=None):
        """Shows discord related info about a user"""
        user = user or ctx.author

        is_bot = ""
        if user.bot: is_bot=" (Bot)"

        embed = discord.Embed(
            colour = self.bot.colour,
            timestamp = datetime.utcnow()
        )
        embed.set_footer(text=self.bot.footer)
        embed.set_thumbnail(url=user.avatar_url)
        embed.set_author(name=str(user)+is_bot)
        embed.add_field(
            name="ID",
            value=user.id,
            inline=False
        )
        embed.add_field(
            name="Created",
            value=datetime.strftime(user.created_at, '%a %d, %B of %Y at %H:%M %p'),
            inline=False
        )
        if isinstance(user, discord.Member):
            embed.add_field(
                name = "Joined",
                value=datetime.strftime(user.joined_at, '%a %d, %B of %Y at %H:%M %p'),
                inline=False
            )

            embed.add_field(
                name="Roles",
                value=' '.join([r.mention for r in user.roles if r != ctx.guild.default_role] or ['None']),
                inline=False
            )
        elif isinstance(user, discord.User):
            embed.description = "*This member is not in this server*"

        await ctx.send(embed=embed)


    @commands.command(aliases=['ri'])
    async def robloxinfo(self, ctx:commands.Context, user:Union[discord.User, discord.Member]=None):
        """Gets roblox related info of a user. Needs to be verified with RoWifi"""
        user = user or ctx.author
        if user.bot:
            return await ctx.send("Discord Bots don't get a fancy Roblox Account.")
        exist = self.cache.get(CacheType.RobloxUser, str(user.id))
        if not exist:
            exist = await self.requests.roblox_info(user.id)
            self.cache.set(CacheType.RobloxUser, str(user.id), exist)

        embed = discord.Embed(
            colour = self.bot.colour,
            timestamp = datetime.utcnow()
        )
        embed.set_footer(text=self.bot.footer)
        embed.set_author(name=str(user))
        
        is_banned = ""
        if exist.is_banned:
            is_banned = " (Banned from Roblox)"

        embed.add_field(
            name="Name",
            value=exist.name+is_banned,
            inline=False
        )

        embed.add_field(
            name="Roblox Id",
            value=exist.id,
            inline=False
        )

        embed.add_field(
            name="Created At",
            value=datetime.strftime(exist.created, '%a %d, %B of %Y at %H:%M %p'),
            inline=False
        )

        embed.add_field(
            name="Profile Link",
            value=f"[Click Here](https://www.roblox.com/users/{exist.id}/profile)",
            inline=False
        )

        embed.set_thumbnail(url=f"http://www.roblox.com/Thumbs/Avatar.ashx?x=150&y=150&Format=Png&username={exist.name}")

        await ctx.send(embed=embed)

def setup(bot:commands.Bot):
    bot.add_cog(Information(bot))