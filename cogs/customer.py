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
        self.update_everyone.start()

    async def fetch_role(self, guild_id:int=RoWifiHQ, role_id:int=CustomerRole) -> Union[discord.Role, None]:
        guild = self.bot.get_guild(guild_id)
        if not guild:
            guild = await self.bot.fetch_guild(guild_id)

        role = guild.get_role(role_id)
        return role

    async def get_roblox_id(self, member:discord.Member) -> Union[int, None]:
        raw = await get(f"https://api.rowifi.link/v1/users/{member.id}")
        if raw['success']:
            return raw['roblox_id']
        else:
            return None

    async def is_in_group(self, roblox_id, group_id=5581309) -> bool:
        groups = await get(f"https://groups.roblox.com/v2/users/{roblox_id}/groups/roles")
        if groups['data']:
            for g in groups['data']:
                if g['group']['id'] == group_id:
                    return True
            else:
                return False
        return False

    async def add_role(self, member:discord.Member, guild_id=RoWifiHQ, role_id=CustomerRole, reason="Is in RoWifi Roblox Group.") -> None:
        role = await self.fetch_role(guild_id=guild_id, role_id=role_id)
        if role:
            return await member.add_roles(role, reason=reason)

    async def remove_role(self, member:discord.Member, guild_id=RoWifiHQ, role_id=CustomerRole, reason="Left RoWifi Roblox Group") -> None:
        role = await self.fetch_role(guild_id=guild_id, role_id=role_id)
        if role:
            return await member.remove_roles(role, reason=reason)


    async def update_all(self, guild_id=RoWifiHQ, role_id=CustomerRole):
        role = await self.fetch_role(guild_id=guild_id, role_id=role_id)
        if role:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                guild = await self.bot.fetch_guild(guild_id)
            
            for member in guild.members:
                if not member.bot:
                    roblox_id = await self.get_roblox_id(member)
                    if roblox_id:
                        a = await self.is_in_group(roblox_id)
                        if a:
                            await self.add_role(member, guild_id=guild_id, role_id=role_id)
                        else:
                            await self.remove_role(member, guild_id=guild_id, role_id=role_id)
            else:
                return True
        return False


    @commands.group(invoke_without_command=True, hidden=True)
    @bot_channel()
    async def update(self, ctx:commands.Context, member:discord.Member=None):
        user = member or ctx.author
        roblox_id = await self.get_roblox_id(user)
        if roblox_id:
            a = await self.is_in_group(roblox_id)
            if a:
                await self.add_role(user, guild_id=RoWifiHQ, role_id=CustomerRole)
            else:
                await self.remove_role(user, guild_id=RoWifiHQ, role_id=CustomerRole)
            
            await ctx.message.add_reaction("<:tick:818793909982461962>")
        else:
            await ctx.send("The user is not verified with RoWifi.")
            await ctx.message.add_reaction("<:x_:811230315648647188>")

    @update.command(name="all")
    @council()
    @commands.cooldown(3, 12, commands.BucketType.guild)
    async def _all(self, ctx:commands.Context):
        await ctx.send("Updating everyone...")
        start = time.perf_counter()
        a = await self.update_all()
        end = time.perf_counter()
        if a:
            await ctx.send(f"Updated everyone. Took {(end-start):.2f} seconds.")
            await ctx.message.add_reaction("<:tick:818793909982461962>")
        else:
            await ctx.send("Unable to use this command right now.")


    @tasks.loop(hours=3.0)
    async def update_everyone(self):
        await self.update_all(guild_id=RoWifiHQ, role_id=CustomerRole)

    @update_everyone.before_loop
    async def before_update_everyone(self):
        await self.bot.wait_until_ready()


    def cog_unload(self):
        self.update_everyone.cancel()
            

def setup(bot:commands.Bot):
    bot.add_cog(Customer(bot))