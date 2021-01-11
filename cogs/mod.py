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

import asyncio
from typing import Optional, Union
import discord
from discord import colour
from discord.errors import LoginFailure

from discord.ext import commands, tasks
from datetime import date, datetime

from utils.checks import is_admin, is_senior_staff, is_staff
from utils.mod import Mod
from utils.converters import to_user, TimeConverter

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
            if not document["type"] in ("unmute","unban"):
                l.append(document)
        Kick = namedtuple('Kick',['boolean','infractions'])
        if len(l)%5==0:
            return Kick(True, len(l))
        else:
            return Kick(False, len(l))

    async def kick_embed(self, ctx:commands.Context, offender:Union[discord.User, discord.Member], infractions:int) -> None:
        inf_id = self.get_inf_id()

        post = {
            "infractionId":inf_id,
            "type":"kick",
            "moderator":self.bot.user.id,
            "offender":offender.id,
            "reason":f"Auto kick after {infractions} infractions"
        }

        insert = self.db.insert(post)
        if insert.acknowledged:
            embed = discord.Embed(colour=discord.Color.red())
            embed.description = f"{offender.mention} has been kicked for violating {infractions} infractions."
            embed.set_footer(text=f"ID: {inf_id}")
            await ctx.send(embed=embed)

            offenderEmbed = discord.Embed(colour=discord.Colour.red(), title=f"You have been kicked from {ctx.guild.name}", timestamp=datetime.utcnow())
            offenderEmbed.description = f"You have been **`kicked`** | Violated {infractions} infractions."
            offenderEmbed.set_footer(text=f"ID: {inf_id}")

            try:
                await offender.send(embed=embed)
            except:
                pass

            LogEmbed = discord.Embed(colour=discord.Color.red(), title="Kick", timestamp=datetime.utcnow())
            LogEmbed.description = f"ID: `{inf_id}`"
            LogEmbed.add_field(name="Offender", value=f"{offender.mention} `({offender.id})`")
            LogEmbed.add_field(name="Moderator",value=self.bot.user.mention, inline=False)
            LogEmbed.add_field(name="Reason", value=f"Violated {infractions} infractions", inline=False)
            LogEmbed.set_footer(text=self.bot.footer)
            LogEmbed.set_thumbnail(url=offender.avatar_url)
            await self.embed_log(ctx=ctx, embed=LogEmbed)
            await offender.kick(reason=f"Violated {infractions} infractions")

    async def after_insert(self, ctx:commands.Context, infractionId:str, offender:Union[discord.User, discord.Member], moderator:Union[discord.User, discord.Member], reason:str, colour:discord.Colour, type1:str, type2:str) -> None:
        embed = discord.Embed(colour=discord.Color.green())
        embed.description = f"{offender.mention} has been **`{type1}`** | *{reason}*"
        embed.set_footer(text=f"ID: {infractionId}")
        await ctx.send(embed=embed)

        LogEmbed = discord.Embed(colour=colour, title="{type1}", description=f"ID: `{infractionId}`", timestamp=datetime.utcnow())
        LogEmbed.add_field(name="Offender", value=f"{offender.mention} `({offender.id})`")
        LogEmbed.add_field(name="Moderator", value=f"<@{ctx.author.id}> `({ctx.author.id})`", inline=False)
        LogEmbed.add_field(name="Reason", value=reason, inline=False)
        LogEmbed.set_footer(text=self.bot.footer)
        LogEmbed.set_thumbnail(url=offender.avatar_url)
        await self.embed_log(ctx=ctx, embed=LogEmbed)

        offenderEmbed = discord.Embed(title=f"You have been {type2} in {ctx.guild.name}",colour=discord.Color.red(), timestamp=datetime.utcnow())
        offenderEmbed.description = f"You have been **`{type2}`** with reason: `{reason}`"
        offenderEmbed.set_footer(text=f"ID: {infractionId}")

        try:
            await offender.send(embed=offenderEmbed)
        except:
            await ctx.send("I tried DMing the user but their DMs are of.", delete_after=5.0)
        

    @commands.command()
    @commands.guild_only()
    @is_staff()
    async def warn(self, ctx:commands.Context, offender: discord.Member,*, reason:str=None):
        """Warn a member

        Args:
            offender : The user to warn
            reason (optional): The reason for the warn.

        """
        if offender == ctx.author:
            return await ctx.send("You can't warn yourself <a:facepalm:797528543490867220>", delete_after=5.0)
        elif offender.top_role > ctx.author.top_role:
            return await ctx.send("You can't warn someone who is above you", delete_after=5.0)
        elif not offender.bot:
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
                await self.after_insert(ctx, inf_id, offender, ctx.author, reason, discord.Colour.green(),"warn", "warned")
                _kick = await self.to_be_kicked(offender.id)
                if (_kick.boolean):
                    await self.kick_embed(ctx, offender, _kick.infractions)

    @warn.error
    async def warn_error(self, ctx:commands.Context, error):
        """Local Error handler for warn command"""
        if isinstance(error, commands.CheckFailure):
            return await ctx.message.delete()
        elif isinstance(error, commands.MissingRequiredArgument):
            if error.param.name == "offender":
                return await ctx.send("You need to provide an `offender`", delete_after=5.0)


    @commands.command(name="mywarns", aliases=["myinf"])
    async def my_warns(self, ctx:commands.Context):
        """Shows your warns

        """
        warns = []
        cursor = self.db.fetch_many({"offender":{"$eq":ctx.author.id}})
        async for document in cursor:
            warns.append(document)
        
        if len(warns) == 0:
            return await ctx.send("You are squeaky clean <a:ThumbsUp:797516959902072894>")
        
        if not len(warns) == 0:
            embed = discord.Embed(colour=self.bot.colour, timestamp=datetime.utcnow())
            embed.description = f"Total Infractions: {len(warns)}"
            embed.set_footer(text=self.bot.footer)
            embed.set_thumbnail(url=ctx.author.avatar_url)
            embed.set_author(name=str(ctx.author))
            for w in warns:
                embed.add_field(
                    name=(w['type']).capitalize(),
                    value=f"ID: `{w['infractionId']}`\n"\
                          f"Reason: {w['reason']}",
                    inline=False
                )

            await ctx.send(embed=embed)

    def get_mute_role(self, ctx:commands.Context) -> discord.Role:
        return discord.utils.get(ctx.guild.roles, id=732818041041190922)

    @commands.command()
    @commands.guild_only()
    @is_staff()
    async def mute(self, ctx:commands.Context, offender:discord.Member,duration:TimeConverter,*, reason:str=None):
        mute_role = self.get_mute_role(ctx)
        if offender == ctx.author:
            return await ctx.send("You can't mute yourself <a:facepalm:797528543490867220>", delete_after=5.0)
        elif offender.top_role > ctx.author.top_role:
            return await ctx.send("You can't mute someone who is above you", delete_after=5.0)
        elif mute_role in offender.roles:
            return await ctx.send(f"{offender} is already muted..")
        elif not offender.bot:
            pass
        else:
            await ctx.message.delete()
            if reason is None:
                reason = "No reason provided..."
            

            inf_id = self.get_inf_id()

            post = {
                "infractionId":inf_id,
                "type":"mute",
                "moderator":ctx.author.id,
                "offender":offender.id,
                "reason":reason
            }

            insert = await self.db.insert(post)

            if insert.acknowledged:
                embed = discord.Embed(colour=discord.Colour.gold())
                embed.description = f"{offender.mention} has been **`muted`** indefinitely | *{reason}*"
                embed.set_footer(text=f"ID: {inf_id}")
                await ctx.send(embed=embed)

                await offender.add_roles(mute_role, reason=reason)

                LogEmbed = discord.Embed(colour=discord.Colour.gold(), title="Mute", description=f"ID: {inf_id}", timestamp=datetime.utcnow())
                LogEmbed.add_field(name="Offender", value=f"<@{offender.id}> `({offender.id})`")
                LogEmbed.add_field(name="Moderator", value=f"<@{ctx.author.id}> `({ctx.author.id})`", inline=False)
                LogEmbed.add_field(name="Reason", value=reason, inline=False)
                LogEmbed.set_footer(text=self.bot.footer)
                LogEmbed.set_thumbnail(url=offender.avatar_url)
                await self.embed_log(ctx, LogEmbed)

                offenderEmbed = discord.Embed(
                    title=f"You have been muted in {ctx.guild.name}",
                    colour=discord.Colour.red(),
                    timestamp=datetime.utcnow(),
                    description=f"You have been **`muted`** indefinitely with reason: {reason}"
                )
                offenderEmbed.set_footer(text=f"ID: {inf_id}")

                try:
                    await offender.send(embed=offenderEmbed)
                except:
                    await ctx.send("I tried DMing the user but their DMs are of.", delete_after=5.0)


                _kick = await self.to_be_kicked(offender.id)
                if (_kick.boolean):
                    await self.kick_embed(ctx, offender, _kick.infractions)
                    

    @mute.error
    async def mute_error(self, ctx:commands.Context, error):
        """Local error handler for mute command"""
        if isinstance(error, commands.CheckFailure):
            return await ctx.message.delete()
        elif isinstance(error, commands.MissingRequiredArgument):
            if error.param.name == "offender":
                return await ctx.send("You need to provide an `offender`", delete_after=5.0)

    
    @commands.command()
    @commands.guild_only()
    @is_staff()
    async def unmute(self, ctx:commands.Context, offender:discord.Member, *,reason:str=None):
        """Unmutes an already muted user

        Args:
            offender : The user to unmute
            reason (optional): The reason for the unmute
        """
        mute_role = self.get_mute_role(ctx)
        if offender.bot:
            return await ctx.send("You can't perform this action on a bot..", delete_after=5.0)
        elif offender.top_role > ctx.author.top_role:
            return await ctx.send("You can't perform this action on someone who is higher than you..", delete_after=5.0)
        elif not mute_role in offender.roles:
            return await ctx.send(f"{offender} is not muted", delete_after=5.0)
        elif mute_role in offender.roles:
            await ctx.message.delete()
            if reason is None:
                reason = "No reason provided..."

            inf_id = self.get_inf_id()

            post = {
                "infractionId":inf_id,
                "type":"unmute",
                "moderator":ctx.author.id,
                "offender":offender.id,
                "reason":reason
            }

            insert = await self.db.insert(post)

            if insert.acknowledged:
                embed = discord.Embed(colour=discord.Colour.blurple())
                embed.description = f"{offender.mention} has been **`unmuted`** | *{reason}*"
                embed.set_footer(text=f"ID: {inf_id}")
                await ctx.send(embed=embed)

                await offender.remove_roles(mute_role, reason=reason)

                LogEmbed = discord.Embed(colour=discord.Colour.blurple(), title="Unmute", description=f"ID: {inf_id}", timestamp=datetime.utcnow())
                LogEmbed.add_field(name="Offender", value=f"<@{offender.id}> `({offender.id})`")
                LogEmbed.add_field(name="Moderator", value=f"<@{ctx.author.id}> `({ctx.author.id})`", inline=False)
                LogEmbed.add_field(name="Reason", value=reason, inline=False)
                LogEmbed.set_footer(text=self.bot.footer)
                LogEmbed.set_thumbnail(url=offender.avatar_url)
                await self.embed_log(ctx, LogEmbed)

                offenderEmbed = discord.Embed(
                    title=f"You have been unmuted in {ctx.guild.name}",
                    colour=discord.Colour.blurple(),
                    timestamp=datetime.utcnow(),
                    description=f"You have been **`unmuted`** with reason: {reason}"
                )
                offenderEmbed.set_footer(text=f"ID: {inf_id}")

                try:
                    await offender.send(embed=offenderEmbed)
                except:
                    await ctx.send("I tried DMing the user but their DMs are of.", delete_after=5.0)

    @unmute.error
    async def unmute_error(self, ctx:commands.Context, error):
        """Local error handler for unmute command"""
        if isinstance(error, commands.CheckFailure):
            return await ctx.message.delete()
        elif isinstance(error, commands.MissingRequiredArgument):
            if error.param.name == "offender":
                return await ctx.send("You need to provide an `offender`", delete_after=5.0)            

    @commands.command(aliases=['removewarn', 'rw'])
    @commands.guild_only()
    @is_staff()
    async def unwarn(self, ctx:commands.Context, infractionId:str,*, reason:str):
        """Removes the warn of a user based on the id

        Args:
            infractionId: The infraction id
            reason (optional): The reason for removing the warn
        """
        if not len(infractionId) == 10:
            return await ctx.send(f"Infraction id: `{infractionId}` is incorrect.", delete_after=5.0)
        fetch = await self.db.fetch({"infractionId":{"$eq":infractionId}})
        if fetch is None:
            return await ctx.send(f"No infraction was found for id: `{infractionId}`", delete_after=5.0)
        else:
            embed = discord.Embed(colour=self.bot.colour)
            embed.add_field(name="Infraction Type", value=fetch["type"].capitalize(), inline=False)
            embed.add_field(name="Offender", value=f"<@{fetch['offender']}> `({fetch['offender']})`", inline=False)
            embed.add_field(name="Moderator", value=f"<@{fetch['moderator']}> `({fetch['moderator']})`", inline=False)
            embed.add_field(name="Reason", value=fetch['reason'])
            embed.set_footer(text=self.bot.footer+f" | ID: {infractionId}")

            await ctx.reply(content=f"Data for the infraction id: `{infractionId}`", embed=embed, mention_author=True)

            await ctx.send(f"Are you sure you want to delete the warn with id : `{infractionId}`? **(Y/N)**")
            
            def check(message:discord.Message):
                return ctx.author == message.author and ctx.channel == message.channel

            try:
                msg = await self.bot.wait_for("message", check=check, timeout=30.0)
                if msg.content.lower() in ("yes", "y"):
                    a = await self.db.delete({"infractionId":{"$eq":infractionId}})
                    if a.acknowledged:
                        LogEmbed = discord.Embed(colour=discord.Colour.greyple())
                        LogEmbed.title = "Removed Warn"
                        LogEmbed.description = f"ID: `{infractionId}`"
                        LogEmbed.add_field(name="Removed by", value=f"{ctx.author.mention} `({ctx.author.id})`")
                        LogEmbed.add_field(name="Reason for removal", value=reason)
                        LogEmbed.add_field(
                            name="About the infraction",
                            inline=False,
                            value=f"Offender: <@{fetch['offender']}> `({fetch['offender']})`\n"\
                                  f"Moderator: <@{fetch['moderator']}> `({fetch['moderator']})`\n"\
                                  f"Reason: {fetch['reason']}"
                        )
                        await self.embed_log(ctx, LogEmbed)
                        return await ctx.send(f"Removed warn : {infractionId}")
                elif msg.content.lower() in ("no", "n"):
                    return await ctx.send("Phew, dodged a bullet there 😮")
                else:
                    return await ctx.send("Cancelling command...")
            except asyncio.TimeoutError:
                return await ctx.send("Timeout reached. Cancelling command")


    @commands.command()
    @commands.guild_only()
    @is_staff()
    async def warns(self, ctx:commands.Context, member:discord.Member=None):
        """Shows warns of a user or the whole guild

        Args:
            member : The user
        """
        if member is None:
            warns = []
            cursor = self.db.fetch_all
            async for document in cursor:
                warns.append(document)

            if len(warns) == 0:
                return await ctx.send("The server is squeaky clean <a:ThumbsUp:797516959902072894>")
            else:
                embed = discord.Embed(colour=self.bot.colour, timestamp=datetime.utcnow())
                embed.description = f"Total Infractions: {len(warns)}"
                embed.set_footer(text=self.bot.footer)
                embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)
                for w in warns:
                    try:
                        embed.add_field(
                            name=((await to_user(ctx=ctx, argument=f"{w['offender']}"))),
                            value=f"Inf type: `{(w['type']).capitalize()}`\n"\
                                f"ID: `{w['infractionId']}`\n"\
                                f"Reason: {w['reason']}\n"\
                                f"Moderator: <@{w['moderator']}> `({w['moderator']})`",
                            inline=False
                        )
                    except:
                        pass
                return await ctx.send(embed=embed)
                


        warns = []
        cursor = self.db.fetch_many({"offender":{"$eq":member.id}})
        async for document in cursor:
            warns.append(document)
        
        if len(warns) == 0:
            return await ctx.send("They are squeaky clean <a:ThumbsUp:797516959902072894>")
        
        if not len(warns) == 0:
            embed = discord.Embed(colour=self.bot.colour, timestamp=datetime.utcnow())
            embed.description = f"Total Infractions: {len(warns)}"
            embed.set_footer(text=self.bot.footer)
            embed.set_thumbnail(url=member.avatar_url)
            embed.set_author(name=str(member), icon_url=member.avatar_url)
            for w in warns:
                embed.add_field(
                    name=(w['type']).capitalize(),
                    value=f"ID: `{w['infractionId']}`\n"\
                          f"Reason: {w['reason']}\n"\
                          f"Moderator: <@{w['moderator']}> `({w['moderator']})`",
                    inline=False
                )

            await ctx.send(embed=embed)


    @commands.command()
    @commands.guild_only()
    @is_senior_staff()
    async def kick(self, ctx:commands.Context, offender:discord.Member, *,reason:str=None):
        """Kicks a user from the server

        Args:
            offender : The user to kick
            reason (optional): The reason for the kick.
        """
        if offender.top_role>ctx.author.top_role:
            return await ctx.send("You can't kick someone who is higher than you", delete_after=5.0)

        await ctx.message.delete()
        if reason is None:
            reason = "No reason provided..."

        inf_id = self.get_inf_id()

        post = {
            "infractionId":inf_id,
            "type":"kick",
            "moderator":ctx.author.id,
            "offender":offender.id,
            "reason":reason
        }

        insert = await self.db.insert(post)
        if insert.acknowledged:
            embed = discord.Embed(colour=discord.Colour.dark_red())
            embed.description = f"{offender.mention} has been **`kicked`** from the server | *{reason}*"
            embed.set_footer(text=f"ID: {inf_id}")
            await ctx.send(embed=embed)


            LogEmbed = discord.Embed(colour=discord.Colour.dark_red(), title="Kick", description=f"ID: {inf_id}", timestamp=datetime.utcnow())
            LogEmbed.add_field(name="Offender", value=f"<@{offender.id}> `({offender.id})`")
            LogEmbed.add_field(name="Moderator", value=f"<@{ctx.author.id}> `({ctx.author.id})`", inline=False)
            LogEmbed.add_field(name="Reason", value=reason, inline=False)
            LogEmbed.set_footer(text=self.bot.footer)
            LogEmbed.set_thumbnail(url=offender.avatar_url)
            await self.embed_log(ctx, LogEmbed)

            offenderEmbed = discord.Embed(
                title=f"You have been kicked in {ctx.guild.name}",
                colour=discord.Colour.red(),
                timestamp=datetime.utcnow(),
                description=f"You have been **`kicked`** with reason: {reason}"
            )
            offenderEmbed.set_footer(text=f"ID: {inf_id}")

            try:
                await offender.send(embed=offenderEmbed)
            except:
                await ctx.send("I tried DMing the user but their DMs are of.", delete_after=5.0)

            await offender.kick(reason=reason)

    @commands.command()
    @commands.guild_only()
    @is_senior_staff()
    async def ban(self, ctx:commands.Context, offender: discord.Member, *,reason:str=None):
        """Bans a user

        Args:
            offender : The user to ban. If the user is not in the server, use `forceban`
            reason (optional): The reason for the ban.
        """
        if offender.top_role>ctx.author.top_role:
            return await ctx.send("You can't ban someone who is higher than you", delete_after=5.0)

        await ctx.message.delete()
        if reason is None:
            reason = "No reason provided..."

        inf_id = self.get_inf_id()

        post = {
            "infractionId":inf_id,
            "type":"ban",
            "moderator":ctx.author.id,
            "offender":offender.id,
            "reason":reason
        }

        insert = await self.db.insert(post)
        if insert.acknowledged:
            embed = discord.Embed(colour=discord.Colour.magenta())
            embed.description = f"{offender.mention} has been **`banned`** from the server | *{reason}*"
            embed.set_footer(text=f"ID: {inf_id}")
            await ctx.send(embed=embed)


            LogEmbed = discord.Embed(colour=discord.Colour.magenta(), title="Ban", description=f"ID: {inf_id}", timestamp=datetime.utcnow())
            LogEmbed.add_field(name="Offender", value=f"<@{offender.id}> `({offender.id})`")
            LogEmbed.add_field(name="Moderator", value=f"<@{ctx.author.id}> `({ctx.author.id})`", inline=False)
            LogEmbed.add_field(name="Reason", value=reason, inline=False)
            LogEmbed.set_footer(text=self.bot.footer)
            LogEmbed.set_thumbnail(url=offender.avatar_url)
            await self.embed_log(ctx, LogEmbed)

            offenderEmbed = discord.Embed(
                title=f"You have been banned in {ctx.guild.name}",
                colour=discord.Colour.red(),
                timestamp=datetime.utcnow(),
                description=f"You have been **`banned`** with reason: {reason}"
            )
            offenderEmbed.set_footer(text=f"ID: {inf_id}")
            offenderEmbed.add_field(name="Appeal form", value="If you believe you have been banned for something you didn't do appeal here: https://forms.gle/Ed5fxSQGqocPzcq66", inline=False)

            try:
                await offender.send(embed=offenderEmbed)
            except:
                await ctx.send("I tried DMing the user but their DMs are of.", delete_after=5.0)

            await offender.ban(reason=reason+f"\nBanned by {ctx.author}", delete_message_days=7)

    @commands.command()
    @commands.guild_only()
    @is_senior_staff()
    async def unban(self, ctx:commands.Context, user:str, *,reason:str=None):
        """Unbans a user

        Args:
            user (str): Either of the following:
                            • id of the user (preferred)
                            • name#discrim
                            • name
        """
        user = await to_user(ctx, user)
        await ctx.message.delete()
        if reason is None:
            reason = "No reason provided..."
        await ctx.guild.unban(user, reason=reason+f"| Unbanned by {ctx.author}")
        

        inf_id = self.get_inf_id()

        post = {
            "infractionId":inf_id,
            "type":"unban",
            "moderator":ctx.author.id,
            "offender":user.id,
            "reason":reason
        }

        insert = await self.db.insert(post)
        if insert.acknowledged:
            embed = discord.Embed(colour=discord.Colour.magenta())
            embed.description = f"{user.mention} has been **`unbanned`** from the server | *{reason}*"
            embed.set_footer(text=f"ID: {inf_id}")
            await ctx.send(embed=embed)


            LogEmbed = discord.Embed(colour=discord.Colour.magenta(), title="Unban", description=f"ID: {inf_id}", timestamp=datetime.utcnow())
            LogEmbed.add_field(name="Offender", value=f"{user.mention} `({user.id})`")
            LogEmbed.add_field(name="Moderator", value=f"<@{ctx.author.id}> `({ctx.author.id})`", inline=False)
            LogEmbed.add_field(name="Reason", value=reason, inline=False)
            LogEmbed.set_footer(text=self.bot.footer)
            LogEmbed.set_thumbnail(url=user.avatar_url)
            await self.embed_log(ctx, LogEmbed)

    @commands.command(aliases=['fban'])
    @is_senior_staff()
    async def forceban(self, ctx:commands.Context, offender:str, *,reason:str=None):
        """Forcebans a user from the server

        **This should only be used if the user is not in the server**

        Args:
            offender (str): Preferably the id of the user to ban
            reason (str): The reason for the ban
        """

        user = await to_user(ctx, offender)
        await ctx.message.delete()
        if reason is None:
            reason = "No reason provided..."
        await ctx.guild.ban(user, reason=reason+f"| Banned by {ctx.author}", delete_message_days=7)

        inf_id = self.get_inf_id()

        post = {
            "infractionId":inf_id,
            "type":"forceban",
            "moderator":ctx.author.id,
            "offender":user.id,
            "reason":reason
        }

        insert = await self.db.insert(post)
        if insert.acknowledged:
            embed = discord.Embed(colour=discord.Colour.dark_teal())
            embed.description = f"{user.mention} has been **`force banned`** from the server | *{reason}*"
            embed.set_footer(text=f"ID: {inf_id}")
            await ctx.send(embed=embed)


            LogEmbed = discord.Embed(colour=discord.Colour.dark_teal(), title="Force Ban", description=f"ID: {inf_id}", timestamp=datetime.utcnow())
            LogEmbed.add_field(name="Offender", value=f"{user.mention} `({user.id})`")
            LogEmbed.add_field(name="Moderator", value=f"{ctx.author.mention} `({ctx.author.id})`", inline=False)
            LogEmbed.add_field(name="Reason", value=reason, inline=False)
            LogEmbed.set_footer(text=self.bot.footer)
            LogEmbed.set_thumbnail(url=user.avatar_url)
            await self.embed_log(ctx, LogEmbed)

    @commands.command(name="reason")
    @is_staff()
    async def _reason(self, ctx:commands.Context, infractionId:str, *,reason:str):
        """Update the reason of an existing infraction

        Args:
            infractionId (str): The infraction id to update
            reason (str): The new reason
        
        """
        if len(infractionId) != 10:
            return await ctx.send("Incorrect infraction id was given", delete_after=5.0)
        fetch = await self.db.fetch({"infractionId":infractionId})
        if not fetch:
            return await ctx.send(f"Infraction with id: {infractionId} does not exist", delete_after=10.0)
        user = await to_user(ctx, str(fetch['offender']))
        update = await self.db.update({"infractionId":infractionId}, {"reason":reason+f" | (new reason by: {ctx.author})"})
        if update.acknowledged:
            await ctx.send("Successfully updated the reason", delete_after=10.0)

            LogEmbed = discord.Embed(colour=discord.Colour.orange(), title="Reason update", timestamp=datetime.utcnow())
            LogEmbed.description=f"ID: {infractionId}"
            LogEmbed.add_field(name="Old Reason", value=fetch['reason'], inline=False)
            LogEmbed.add_field(name="New Reason", value=reason+f" | (new reason by: {ctx.author})", inline=False)
            LogEmbed.add_field(name="Info", value=f"For more info on the infraction use `.inf {infractionId}`")
            LogEmbed.set_footer(text=self.bot.footer)
            LogEmbed.set_thumbnail(url=user.avatar_url)
            await self.embed_log(ctx, LogEmbed)

    @commands.command(aliases=['infraction'])
    @is_staff()
    async def inf(self, ctx:commands.Context, infractionId:str):
        """Shows info about the infraction related with its id

        Args:
            infractionId (str): The id of the infraction
        """
        if len(infractionId) != 10:
            return await ctx.send("Incorrect infraction id was given", delete_after=10.0)
        fetch = await self.db.fetch({"infractionId":infractionId})
        if fetch:
            user = await to_user(ctx, str(fetch['offender']))
            mod = await to_user(ctx, str(fetch['moderator']))
            embed = discord.Embed(colour=self.bot.colour)
            embed.description = f"ID: `{infractionId}`"
            embed.add_field(name="Type", value=fetch['type'].capitalize(), inline=False)
            embed.add_field(name="Offender", value=str(user), inline=False)
            embed.add_field(name="Moderator", value=str(mod), inline=False)
            embed.add_field(name="Reason", value=fetch['reason'])
            embed.set_thumbnail(url=user.avatar_url)
            embed.set_footer(text=self.bot.footer)
            return await ctx.send(embed=embed)
        else:
            return await ctx.send(f"Could not find an infraction with id: {infractionId}")


    @commands.command(aliases=['clean'])
    @is_staff()
    async def purge(self, ctx:commands.Context, limit:int, bulk:Optional[bool]=True):
        """Used to delete messages

        Args:
            limit (int): The amount of messages to delete
            bulk (optional): Whether to bulk delete or not. Defaults to True.
        """
        def check(msg:discord.Message):
            return not msg.pinned

        deleted = await ctx.channel.purge(limit=limit+1, check=check, bulk=bulk)
        
        await ctx.send(f"Deleted {len(deleted)} messages.", delete_after=5.0)

        LogEmbed = discord.Embed(title="Purge", colour=discord.Colour.dark_blue(), timestamp=datetime.utcnow())
        LogEmbed.description = f"Purged **{len(deleted)}** messages in {ctx.channel.mention}"
        LogEmbed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)
        LogEmbed.set_footer(text=self.bot.footer)
        await self.embed_log(ctx, LogEmbed)

    @commands.command(aliases=['tmute', 'tm'], usage="<offender> <hours> [reason]")
    @is_staff()
    async def tempmute(self, ctx:commands.Context, offender:discord.Member, hours:Optional[int]=None, *, reason:str=None):
        """Temporary mutes the offender

        Args:
            offender : The user to temporary mute
            hours (int): The number of hours to mute. MUST BE A NUMBER LIKE `1`, `3` or `4`
            reason (optional): The reason for the mute.
        """
        if reason is None:
            reason = "No reason provided..."
        if hours is None:
            hours = 3
        inf_id = self.get_inf_id()
        a = datetime.utcnow()
        b = datetime(a.year, a.month, a.day, a.hours+hours, a.minute, a.second, a.microsecond)
        post = {
            "infractionId":inf_id,
            "type":"forceban",
            "moderator":ctx.author.id,
            "offender":offender.id,
            "reason":reason + f" | Until {datetime.strftime(b, '%a %d, %B of %Y at %H:%M%p')} ({hours} hours)",
            "mute_time": b
        }

        insert = await self.db.insert(post)

        if insert.acknowledged:
            embed = discord.Embed(colour=discord.Color.red())
            embed.description = f"{offender.mention} has ben muted for {hours}h | *{reason}*"
            embed.set_footer(text=f"ID: {inf_id}")

            LogEmbed = discord.Embed(colour=discord.Color.red(), title="Temporarily Muted", timestamp=datetime.utcnow())
            LogEmbed.description = f"ID: {inf_id}"
            LogEmbed.add_field(name="Offender", value=f"{offender.mention} `({offender.id})`", inline=False)
            LogEmbed.add_field(name="Moderator", value=f"{ctx.author.mention} `({ctx.author.id})`", inline=False)
            LogEmbed.add_field(name="Duration", value=f"Until {datetime.strftime(b, '%a %d, %B of %Y at %H:%M%p')} ({hours} hours)")
            LogEmbed.add_field(name="Reason", value=reason, inline=False)
            LogEmbed.set_thumbnail(url=offender.avatar_url)
            LogEmbed.set_footer(text=self.bot.footer)
            await self.embed_log(ctx, LogEmbed)

    @commands.command()
    async def test(self, ctx:commands.Context):
        await ctx.send("Before")
        await asyncio.sleep(30)
        await ctx.send("After")

def setup(bot:commands.Bot):
    bot.add_cog(Moderation(bot))