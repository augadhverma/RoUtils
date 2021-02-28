import discord
import time
import platform

from typing import Optional, Union
from discord.ext import commands
from datetime import datetime

from utils.cache import Cache, CacheType
from utils.classes import RobloxUser
from utils.requests import get
from utils.errors import RobloxUserNotFound
from utils.checks import bot_channel
from utils.db import Connection

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
        self.tag_db = Connection("Utilities","Tags")


    @commands.command(aliases=['ui'])
    @bot_channel()
    async def userinfo(self, ctx:commands.Context, *, user:Union[discord.Member, discord.User]=None):
        """Shows discord related info about a user."""
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
    @bot_channel()
    async def robloxinfo(self, ctx:commands.Context, user:Union[discord.User, discord.Member]=None):
        """Gets roblox related info of a user. Needs to be verified with RoWifi."""
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

    @commands.command()
    @bot_channel()
    async def ping(self, ctx:commands.Context):
        """Shows the bot ping."""
        start = time.perf_counter()
        msg = await ctx.send("Pinging...")
        end = time.perf_counter()
        duration = (end-start)*1000

        db_start = time.perf_counter()
        await self.tag_db.count_documents({})
        db_end = time.perf_counter()
        db_duration = (db_end - db_start)*1000

        embed = discord.Embed(
            colour = self.bot.colour,
            timestamp = datetime.utcnow()
        )

        embed.set_footer(text=self.bot.footer)

        embed.add_field(
            name="<a:typing:800335819764269096> | Typing",
            value=f"`{duration:.2f}ms`"
        )

        embed.add_field(
            name="<:routils:802250413973831712> | Websocket",
            value=f"`{(self.bot.latency*1000):.2f}ms`"
        )

        embed.add_field(
            name="<:mongo:814706574928379914> Database",
            value=f"`{db_duration:.2f}ms`"
        )

        await msg.edit(embed=embed, content="")


    @commands.command()
    @bot_channel()
    async def botinfo(self, ctx:commands.Context):
        """Shows botinfo"""
        embed = discord.Embed(
            title="Bot Info",
            colour = self.bot.colour,
            timestamp = datetime.utcnow()
        )
        embed.description = "A multi-purpose bot to keep the RoWifi server a cool place."
        embed.set_footer(text=self.bot.footer)
        embed.set_thumbnail(url=self.bot.user.avatar_url)

        embed.add_field(
            name="Developer",
            value="[ItsArtemiz](https://discord.com/users/449897807936225290)"
        )
        embed.add_field(
            name="Python Version",
            value=platform.python_version()
        )
        embed.add_field(
            name="Discord.py Version",
            value=discord.__version__
        )
        embed.add_field(
            name="Bot Version",
            value=self.bot.version
        )
        embed.add_field(
            name="Server",
            value=platform.system()
        )

        embed.add_field(
            name="Total Commands",
            value=len(self.bot.commands)
        )

        await ctx.send(embed=embed)

    @commands.command()
    @bot_channel()
    async def spotify(self, ctx:commands.Context, user:Optional[discord.Member]):
        """Shows the spotify status of a user"""
        user = user or  ctx.author
        if user.activity is None:
            return await ctx.send(f"**{user}** is not listening to spotify currently.")
        if isinstance(user.activities[0], discord.activity.Spotify):
            activity:discord.Spotify = user.activities[0]
            embed = discord.Embed(
                title = activity.title,
                colour = activity.colour,
                timestamp = activity.start,
                url = f"https://open.spotify.com/track/{activity.track_id}"
            )
            embed.set_footer(text=f"Started listening at")
            embed.set_thumbnail(url=activity.album_cover_url)
            if len(activity.artists) > 1:
                artists = ", ".join([a for a in activity.artists])
            else:
                artists = activity.artist
            embed.description = f"**Artists:** {artists}\n**Album:** {activity.album}\n**Duration:** {str(activity.duration)[2:-7]}"
            await ctx.send(embed=embed)
        else:
            return await ctx.send(f"**{user}** is not listening to spotify currently.")

def setup(bot:commands.Bot):
    bot.add_cog(Information(bot))