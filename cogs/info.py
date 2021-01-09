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
from discord.ext import commands
from datetime import date, datetime

from utils.requests import get
import typing

class Information(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot

    @commands.command(aliases=['ui','i'])
    @commands.cooldown(1,3.0,commands.BucketType.member)
    async def userinfo(self, ctx:commands.Context, member:typing.Union[discord.Member, discord.User]=None):
        if member is None:
            member = ctx.author

        status = {
            "online":"<:online:789399319727046696> `Online`",
            "offline":"<:offline:789399319915790346> `Offline`",
            "dnd":"<:dnd:789399319400153098> `Do Not Disturb`",
            "idle":"<:idle:789399320029560852> `Idle`"
        }
        try:
            s = f"Status: {status[str(member.status)]}\n"
        except:
            s = "Status: `Cannot find status in DMs`\n"

        embed = discord.Embed(title="User Information", colour=member.colour, timestamp=datetime.utcnow())
        embed.add_field(name="General Info", 
                        value=f"Name: `{member}`\n"
                              f"{s}"
                              f"Created at: `{datetime.strftime(member.created_at, '%a %d, %B of %Y at %H:%M%p')}`",
                        inline=False)

        if not isinstance(member, discord.User):
            embed.add_field(name="Server Related",
                            value=f"Joined us at: `{datetime.strftime(member.joined_at, '%a %d, %B of %Y at %H:%M%p')}`\n"
                                  f"Roles: {' '.join([r.mention for r in member.roles if r != ctx.guild.default_role] or ['None'])}\n"
                                  f"Staff: `{652203841978236940 in [r.id for r in member.roles]}`",
                            inline=False)

        roblox_id = (await get(f"https://api.rowifi.link/v1/users/{member.id}"))['roblox_id']

        try:
            embed.set_thumbnail(url=f"http://www.roblox.com/Thumbs/Avatar.ashx?x=420&y=420&Format=Png&userId={roblox_id}")
        except:
            embed.set_thumbnail(url=member.avatar_url)

        await ctx.send(embed=embed)
    

def setup(bot:commands.Bot):
    bot.add_cog(Information(bot))