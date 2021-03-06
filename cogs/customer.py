from typing import Optional
import discord
from discord.ext import tasks, commands

from utils.requests import get, HTTPException
from utils.checks import bot_channel

RoWifiHQ = 576325772629901312
CustomerRole = 581428516269064203

class Customer(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot

    def cog_unload(self):
        self.customer_role_loop.cancel()

    async def get_or_fetch_guild(self) -> discord.Guild:
        guild = self.bot.get_guild(RoWifiHQ)
        if guild is None:
            guild = await self.bot.fetch_guild(RoWifiHQ)
        return guild

    async def get_customer_role(self) -> discord.Role:
        guild = await self.get_or_fetch_guild()
        role = guild.get_role(CustomerRole)
        return role

    async def give_customer_role(self, member:discord.Member):
        if member.guild.id != RoWifiHQ:
            return
        role = await self.get_customer_role()
        try:
            await member.add_roles(role, reason="The user is in RoWifi Roblox group.")
        except discord.Forbidden as e:
            raise e

    async def remove_customer_role(self, member:discord.Member):
        if member.guild.id != RoWifiHQ:
            return
        role = await self.get_customer_role()
        try:
            await member.remove_roles(role, reason="Left RoWifi Roblox group.")
        except discord.Forbidden as e:
            raise e

    async def get_roblox_id(self, member:discord.Member) -> Optional[int]:
        raw = await get(f"https://https://api.rowifi.link/v1/users/{member.id}")
        if raw['success']:
            return raw['roblox_id']
        else:
            return None

    async def is_in_group(self, roblox_id:int) -> bool:
        try:
            groups:list = await get(f"https://groups.roblox.com/v2/users/{roblox_id}/groups/roles")
        except HTTPException:
            return False
        
        if groups:
            for group in groups:
                if group['group']['id'] == RoWifiHQ:
                    return True
            return False
        else:
            return False

    async def do_customer_thing(self, member:discord.Member) -> bool:
        roblox_id = await self.get_roblox_id(member)
        if roblox_id:
            is_in_group = await self.is_in_group(roblox_id)
            if is_in_group:
                await self.give_customer_role(member)
                return True
            else:
                await self.remove_customer_role(member)
                return False
        else:
            return False

    @tasks.loop(hours=1.0)
    async def customer_role_loop(self):
        guild = await self.get_or_fetch_guild()
        for member in guild.members:
            await self.do_customer_thing(member)

    @commands.command(hidden=True)
    @bot_channel()
    async def update(self, ctx:commands.Context, user:Optional[discord.Member]):
        user = user or ctx.author
        customer_thing = await self.do_customer_thing(user)
        await ctx.send(customer_thing)
        if customer_thing:
            await ctx.send("\U0001f44c")
        else:
            await ctx.send(f"**{user}** is not verified with RoWifi.")
        

def setup(bot:commands.Bot):
    bot.add_cog(Customer(bot))