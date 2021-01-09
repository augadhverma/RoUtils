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
from typing import Union

from discord.ext import commands, tasks
from datetime import datetime

from utils.checks import is_admin, is_senior_staff, is_staff
from utils.mod import Mod

import random
import string

from collections import namedtuple

class Moderation(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        self.db = Mod("Infractions")

    def get_inf_id(self) -> str:
        """Returns a random generated infraction id

        Returns:
            str: A random infraction id
        """
        res = "".join(random.choices(string.ascii_lowercase+string.ascii_uppercase+string.digits, k=10))
        return res

    async def embed_log(self, ctx:commands.Context, embed:discord.Embed):
        """Universal embed logger

        Args:
            ctx (commands.Context): The context
            embed (discord.Embed): The discord.Embed
        """
        channel:discord.TextChannel = discord.utils.get(ctx.guild.text_channels, name="bot-logs")
        if not channel is None:
            try:
                await channel.send(embed=embed)
            except:
                pass

    
    async def to_be_kicked(self, offender:int) -> namedtuple:
        """Checks if the offender needs to be kicked after 5 infractions

        Args:
            offender (int): The id of the offender

        Returns:
            bool: Reutrns `True` if the infractions is 5 else returns `False`
        """
        l = []
        cursor = self.db.fetch_many({"offender":{"$eq":offender}})
        async for document in cursor:
            l.append(document)
        Kick = namedtuple('Kick',['boolean','infractions'])
        if len(l)%5==0:
            print(Kick(True, len(l)))
            return Kick(True, len(l))
        else:
            print(Kick(False, len(l)))
            return Kick(False, len(l))
        

    @commands.command()
    @commands.guild_only()
    @is_staff()
    async def warn(self, ctx:commands.Context, offender: Union[discord.Member, discord.User],*, reason:str=None):
        await ctx.message.delete()
        if reason is None:
            reason = "No reason provided..."

        inf_id = self.get_inf_id()

        post = {
            "infractionId":inf_id,
            "type":"warn",
            "moderator":ctx.author.id,
            "offender":offender.id,
            "reason":reason
        }

        insert = await self.db.insert(post)

        
        if insert.acknowledged:
            embed = discord.Embed(colour=discord.Color.green())
            embed.description = f"{offender} has been **`warned`** | *{reason}*"
            embed.set_footer(text=f"ID: {inf_id}")
            await ctx.send(embed=embed)

            LogEmbed = discord.Embed(colour=discord.Colour.green(), title="Warn", description=f"ID: `{inf_id}`", timestamp=datetime.utcnow())
            LogEmbed.add_field(name="Offender", value=f"<@{offender.id}> `({offender.id})`")
            LogEmbed.add_field(name="Moderator", value=f"<@{ctx.author.id}> `({ctx.author.id})`", inline=False)
            LogEmbed.add_field(name="Reason", value=reason, inline=False)
            LogEmbed.set_footer(text=self.bot.footer)
            LogEmbed.set_thumbnail(url=offender.avatar_url)
            await self.embed_log(ctx=ctx, embed=LogEmbed)

            offenderEmbed = discord.Embed(title=f"You have been warned in {ctx.guild.name}",colour=discord.Color.red(), timestamp=datetime.utcnow())
            offenderEmbed.description = f"You have been **`warned`** with reason: `{reason}`"
            offenderEmbed.set_footer(text=f"ID: {inf_id}")

            try:
                await offender.send(embed=offenderEmbed)
            except:
                await ctx.send("I tried DMing the user but their DMs are of.", delete_after=5.0)
            _kick = await self.to_be_kicked(offender.id)
            print(_kick[0], _kick[1])
            print(_kick.boolean, _kick.infractions)
            if (_kick.boolean):
                new_inf_id = self.get_inf_id()
                embed = discord.Embed(colour=discord.Colour.red())
                embed.description = f"{offender} has been **`kicked`** | *Violated {_kick.infractions} infractions.*"
                embed.set_footer(text=f"ID: {new_inf_id}")

                offenderEmbed = discord.Embed(title=f"You have been kicked from {ctx.guild.name}", colour=discord.Color.red(), timestamp=datetime.utcnow())
                offenderEmbed.description = f"You have been **`kicked`** with reason: `Violated {_kick.infractions} infractions`. "
                offenderEmbed.set_footer(text=f"ID: {new_inf_id}")
                await ctx.send(embed=embed)
                try:
                    await offender.send(embed=offenderEmbed)
                except:
                    pass

                LogEmbed = discord.Embed(colour=discord.Color.red(), title="Kick", timestamp=datetime.utcnow())
                LogEmbed.description = f"ID: `{new_inf_id}`"
                LogEmbed.add_field(name="Offender", value=f"<@{offender.id}> `({offender.id})`")
                LogEmbed.add_field(name="Moderator",value=self.bot.user.mention, inline=False)
                LogEmbed.add_field(name="Reason", value=f"Violated {_kick.infractions} infractions", inline=False)
                LogEmbed.set_footer(text=self.bot.footer)
                LogEmbed.set_thumbnail(url=offender.avatar_url)
                await self.embed_log(ctx=ctx, embed=LogEmbed)
                await offender.kick(reason=f"Violated {_kick.infractions} infractions")


    @commands.command()
    async def test(self, ctx:commands.Context):
        c = self.db.fetch_many({"offender":{"$eq":173977882765426688}})
        async for document in c:
            await ctx.send(document)
def setup(bot:commands.Bot):
    bot.add_cog(Moderation(bot))        
