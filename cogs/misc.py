"""
Miscellaneous Commands.

Copyright (C) 2021  ItsArtemiz (Augadh Verma)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>
"""

import asyncio
import discord
import time
import datetime as dt
import humanize
import psutil


from bot import RoUtils
from discord.ext import commands
from typing import Optional, Union

from utils.checks import admin, botchannel, intern, staff
from utils.paginator import jskpagination
from utils.logging import post_log
from utils.time import human_time

class Miscellaneous(commands.Cog):
    def __init__(self, bot:RoUtils):
        self.bot = bot
        self.process = psutil.Process()
        self._afk = dict()

    @intern()
    @commands.group(invoke_without_command=True)
    async def afk(self, ctx:commands.Context, *,reason:commands.clean_content=None):
        """ Sets an AFK status for maximum 24 hours """

        reason = reason or "Gone for idk how much long."

        d = self._afk.get(ctx.author.id, None)
        if d is None:
            self._afk[ctx.author.id] = (time.time(), reason)
        else:
            return await ctx.reply("You are already AFK'ed")

        await ctx.reply(f"Alright {ctx.author.name}, I have set your AFK.", delete_after=5.0)

    @admin()
    @afk.command(name="list")
    async def afklist(self, ctx:commands.Command):
        await ctx.send(self._afk)

    @admin()
    @afk.command(name="remove")
    async def afkremove(self, ctx:commands.Context, *, user:discord.User):
        if user.id in list(self._afk.keys()):
            del self._afk[user.id]
            await ctx.send(f"Succesfully removed {user.name} from the afk list.")
        else:
            await ctx.send("That user is not currently AFKed.")

    @admin()
    @afk.command(name="set")
    async def setafk(self, ctx:commands.Context, user:discord.User, *,reason:commands.clean_content):
        d = self._afk.get(user.id, None)
        if d is None:
            self._afk[user.id] = (time.time(), reason)
        else:
            return await ctx.reply("You are already AFK'ed")

        await ctx.reply(f"Alright {user.name}, I have set your AFK.", delete_after=5.0)


    @commands.Cog.listener()
    async def on_message(self, message:discord.Message):
        if isinstance(message.channel, discord.DMChannel):
            return

        if message.author.bot:
            return

        user = self._afk.get(message.author.id, None)
        if user is not None:
            if (time.time() - user[0]) <= 5.0:
                pass
            else:
                await message.channel.send(f"{message.author.mention} I have removed your AFK status", delete_after=5.0)

                del self._afk[message.author.id]

        for user in message.mentions:
            afked = self._afk.get(user.id, None)
            if afked is None:
                pass
            else:
                await message.channel.send(f"{message.author.mention}, {user.name} has been AFK for {humanize.naturaldelta(dt.timedelta(seconds=time.time() - afked[0]))} with reason: {afked[1]}")

    @botchannel()
    @commands.command()
    async def ping(self, ctx:commands.Context):
        """ Shows bot ping. """

        start = time.perf_counter()
        m:discord.Message = await ctx.send('Pinging...')
        end = time.perf_counter()
        duration = (end-start)*1000

        embed = discord.Embed(
            colour = self.bot.invisible_colour
        )
        embed.add_field(
            name="<a:typing:828718094959640616> | Typing",
            value=f"`{duration:.2f}ms`"
        )
        embed.add_field(
            name="<:stab:828715097407881216> | Websocket",
            value=f"`{(self.bot.latency*1000):.2f}ms`"
        )

        tag_s = time.perf_counter()
        await self.bot.tag_db.count_documents({})
        tag_e = time.perf_counter()
        tag = (tag_e - tag_s)*1000

        mod_s = time.perf_counter()
        await self.bot.mod_db.count_documents({})
        mod_e = time.perf_counter()
        mod = (mod_e - mod_s)*1000

        embed.add_field(
            name='<:mongo:814706574928379914> | Database Connections',
            value=f'**Tags:** `{tag:.2f}ms` | **Moderation:** `{mod:.2f}ms`'
        )

        await m.edit(content=None, embed=embed)

    @botchannel()
    @commands.command()
    async def msgraw(self, ctx:commands.Context, message_id:int, channel_id:Optional[int]):
        """ Returns raw content of a message.
        If the message is from another channel, then you have to provide it aswell """

        channel_id = channel_id or ctx.channel.id

        content = await self.bot.http.get_message(channel_id=channel_id, message_id=message_id)

        await jskpagination(ctx, str(content), wrap_on=(','))

    @botchannel()
    @commands.command(name="id",aliases=['getid'])
    async def getid(self, ctx:commands.Context, *, object:Union[discord.User, discord.Role, discord.TextChannel]):
        """ Gives you id of a role, user or text channel """
        try:
            await ctx.send(f"`{object.id}`")
        except commands.BadUnionArgument:
            await ctx.send(f"Cannot get id for {object}")

    @botchannel()
    @commands.command()
    async def news(self, ctx:commands.Context):
        """ Shows Bot News and Feature plans. """
        news = "The bot is currently in development mode. New features are being added "\
               "to it constantly. The current working features are: "\
               "`AFK Feature`, `Tags Handling`, `Userinfo (Roblox and Discord)`, `Moderation Stuff`\n\n"\
               "The features being worked on are: `Automoderation`, `Ticket Handling System`.\n"\
               "I plan on updating the bot as soon the Moderation Features are done with its testing phase, "\
               "and this is also when RoUtils will go open source."

        date = dt.datetime.utcnow().strftime('%B %d, %Y')

        embed = discord.Embed(
            title = f"\U0001f4f0 Latest News - {date} \U0001f4f0",
            description = news,
            colour = self.bot.invisible_colour
        )

        await ctx.send(embed=embed)
    
    @staff()    
    @commands.command()
    async def notify(self, ctx:commands.Context, member:discord.Member, *, text:str):
        """Notifies a user about something.
        
        Helper Texts
        -------------
        `ad`: Notifies the user about their ad not following advertisement rules."""
        
        if text.lower() == 'ad':
            text = "Your advertisement was deleted because it doesn't follow our advertisement rules."
            
        embed = discord.Embed(
            title = "Notification from RoWifi Staff",
            description = text,
            timestamp = dt.datetime.utcnow(),
            colour = discord.Colour.magenta()
        )
            
        try:
            await member.send(embed=embed)
        except discord.Forbidden:
            await ctx.send(f"Couldn't send the message to {member}")
        finally:
            embed.add_field(
                name = "From",
                value = f"{ctx.author.mention} `({ctx.author.id})`",
                inline=False
            )
            
            embed.add_field(
                name = "To",
                value = f"{member.mention} `({member.id})`",
                inline=False
            )
            
            await post_log(ctx.guild, name='bot-logs', embed=embed)
            
    @admin()
    @commands.group(invoke_without_command=True)
    async def role(self, ctx:commands.Context, member:commands.Greedy[discord.Member], role:commands.Greedy[discord.Role]):
        """ Adds a role to a member. 
        
        You can provide multiple users at once aswell."""
        if not member and not role:
            return await ctx.send_help(self.role)
        for m in member:
            try:
                await m.add_roles(*role),
            except Exception as e:
                await ctx.send(e)
        await ctx.message.add_reaction('<:tick:818793909982461962>')
    @botchannel()
    @role.command()
    async def info(self, ctx:commands.Context, *, role:discord.Role):
        """ Shows info on a role. """
        embed = discord.Embed(
            title = "Role Info",
            colour = role.colour,
            timestamp = role.created_at
        )
        embed.set_footer(text='Created At')
        embed.description = f'Name: {role.name}\n'\
                            f'ID: `{role.id}`\n'\
                            f'Members: {len(role.members)}\n'\
                            f'Colour: {role.colour}'
            
        msg = await ctx.send(embed=embed)
        if ctx.author.guild_permissions.administrator and len(role.members) <= 30:
            await msg.add_reaction('<:member:824903975299973120>')
            
            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) == '<:member:824903975299973120>'

            try:
                reaction, user = await self.bot.wait_for('reaction_add', check=check, timeout=30.0)
            except asyncio.TimeoutError:
                pass
            else:
                embed.add_field(
                    name='Members',
                    value='\n'.join([f'{m.mention}' for m in role.members]) or 'None',
                    inline=False
                )
                
                await msg.edit(content=None, embed=embed)
            finally:
                await msg.clear_reaction('<:member:824903975299973120>')
                
    @admin()
    @role.command()
    async def remove(self, ctx:commands.Context, member:commands.Greedy[discord.Member], role:commands.Greedy[discord.Role]):
        """ Removes a role from user(s)"""
        for m in member:
            try:
                await m.remove_roles(*role)
            except Exception as e:
                await ctx.send(e)
                
        await ctx.message.add_reaction('<:tick:818793909982461962>')
        
    @admin()
    @role.command(name='all')
    async def roleall(self, ctx:commands.Context, role:commands.Greedy[discord.Role]):
        """ Roles everyone a role"""
        await ctx.message.add_reaction('\U000025b6')
        count = 0
        for member in ctx.guild.members:
            if count>0 and count//10 == 0:
                await asyncio.sleep(5.0)
            try:
                await member.add_roles(*role)
            except Exception as e:
                await ctx.send(e)
        else:
            await ctx.message.add_reaction('<:tick:818793909982461962>')
            
    @admin()
    @role.command(name='rall', aliases=['removeall'])
    async def rall(self, ctx:commands.Context, role:commands.Greedy[discord.Role]):
        """ Removes a role from everyone. """
        await ctx.message.add_reaction('\U000025b6')
        count = 0
        for member in ctx.guild.members:
            if count>0 and count//10 == 0:
                await asyncio.sleep(5.0)
            try:
                await member.remove_roles(*role)
            except Exception as e:
                await ctx.send(e)
        else:
            await ctx.message.add_reaction('<:tick:818793909982461962>')

    @botchannel()
    @commands.command(name='about')
    async def about(self, ctx:commands.Context):
        """Tells you info about the bot"""
        
        a = '<:arrow:849938169477857321>'

        embed = discord.Embed(colour = self.bot.invisible_colour)

        embed.set_author(name=f'{self.bot.user} | v{self.bot.version}', icon_url=self.bot.user.avatar_url)

        text = 0
        voice = 0

        for guild in self.bot.guilds:
            for channel in guild.channels:
                if isinstance(channel, discord.TextChannel):
                    text += 1
                elif isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
                    voice += 1

        memory_usage = self.process.memory_full_info().uss / 1024**2
        cpu_usage = self.process.cpu_percent() / psutil.cpu_count()

        embed.add_field(
            name='General Info',
            value=f'{a} **Developer:** ItsArtemiz#8858\n'\
                  f'{a} **Library:** [discord.py v{discord.__version__}](https://github.com/Rapptz/discord.py \'discord.py GitHub\')\n'\
                  f'{a} **Created:** {human_time(self.bot.user.created_at)}',
            inline=False
        )

        embed.add_field(
            name='Stats',
            value=f'{a} **Commands Loaded:** {len(self.bot.commands)}\n'\
                  f'{a} **RAM Usage:** {memory_usage:.2f}MiB\n'\
                  f'{a} **CPU Usage:** {cpu_usage:.2f}%\n'\
                  f'{a} **Users:** {len(self.bot.users)}\n'\
                  f'{a} **Channels:** <:text:824903975626997771> {text} | <:voice:824903975098777601> {voice}'
        )

        embed.set_footer(text='RoUtils is a private bot created to manage the RoWifi HQ server.')

        await ctx.send(embed=embed)
def setup(bot:RoUtils):
    bot.add_cog(Miscellaneous(bot))
