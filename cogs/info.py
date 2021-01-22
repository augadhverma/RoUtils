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
import discord
from discord.ext import commands
from datetime import datetime
from jishaku import Jishaku

from utils.requests import get
from utils.checks import bot_channel

import typing
import psutil
import platform, multiprocessing, inspect

class Information(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot

    @commands.command(aliases=['ui','i'])
    @commands.cooldown(1,3.0,commands.BucketType.member)
    @bot_channel()
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

    @commands.command()
    @bot_channel()
    async def get_id(self, ctx:commands.Context) -> int:
        """Get your discord id

        """
        await ctx.send(f"You discord id is: `{ctx.author.id}`")

    @commands.command(aliases=['app','apps','applications', 'application'])
    @bot_channel()
    async def apply(self, ctx:commands.Context):
        """Gives the support staff application

        """
        await ctx.send("Support Staff application: https://forms.gle/qvEMjT8RweVmJQW99")


    @commands.command()
    @bot_channel()
    async def api(self, ctx:commands.Context, member:discord.Member=None):
        if not member:
            member=ctx.author

        e = discord.Embed(colour=self.bot.colour, title="RoWifi Users API", timestamp=datetime.utcnow())
        e.description = f"Base: `https://api.rowifi.link/v1/users/<USERID>`\n\nExample: https://api.rowifi.link/v1/users/{member.id}"
        e.add_field(
            name="Responses",
            value='• If user is verified:\n`{"success":true,"discord_id":int,"roblox_id":int}`\n\n• If user is not verified:\n`{"success":false,"message":"User is not verified in the RoWifi database"}`'
        )
        e.add_field(
            name="Ratelimits",
            value="At the moment, there are no ratelimits",
            inline=False
        )
        e.set_author(name=str(member), icon_url=member.avatar_url)

        await ctx.send(embed=e)
    
    @commands.command(aliases=['prefixes'])
    @bot_channel()
    async def prefix(self, ctx:commands.Context):
        """Shows all the prefix of the bot"""
        embed = discord.Embed(title="Prefixes", colour=self.bot.colour)
        embed.set_footer(text=f"{len(self.bot.prefixes)} prefixes")
        embed.description = '\n'.join(f'{index}. {elem}' for index, elem in enumerate(self.bot.prefixes, 1))
        await ctx.send(embed=embed)


    @commands.command()
    @bot_channel()
    async def stats(self, ctx:commands.Context):
        """Shows Bot Statistics"""
        embed = discord.Embed(title="<a:loading:801422257221271592> Gathering Stats", colour=self.bot.colour)
        msg = await ctx.send(embed=embed)
        channel_types = typing.Counter(type(c) for c in self.bot.get_all_channels())
        voice = channel_types[discord.channel.VoiceChannel]
        text = channel_types[discord.channel.TextChannel]
        infoembed = discord.Embed(
            title="<a:settings:801424449542815744> Stats",
            description=f"<:member:789445545915580486> Member Count: `{len(self.bot.users)}`\n<:discord:801425079937663017> Servers: `{len(self.bot.guilds)}`\n<:code:801425080936038400> Commands: `{len(self.bot.commands)}`\n<:text:789428500003029013> Text Channels: `{text}`\n<:voice:789428500309475408> Voice Channels: `{voice}`\n<:dpy:789493535501058078> DPY Version: `{discord.__version__}`\n<:python:789493535493718026> Python Version: `{platform.python_version()}`\n<:server:801426535637712956> Server: `{platform.system()}`\n> CPU Count: `{multiprocessing.cpu_count()}`\n> CPU Usage: `{psutil.cpu_percent()}%`\n> RAM: `{psutil.virtual_memory().percent}%`",
            colour=self.bot.colour
        )
        infoembed.set_footer(text=self.bot.version)
        await asyncio.sleep(2)
        await msg.edit(embed=infoembed)

    @commands.command(aliases=['src'])
    @bot_channel()
    async def source(self, ctx:commands.Context, *, command:str=None):
        if not command:
            embed = discord.Embed(title="Here is my source code.",
                                  description="Don't forget the license! (A star would also be appreciated ^^)",
                                  url=ctx.bot.github_url, colour=ctx.bot.colour)
            return await ctx.send(embed=embed)

        command = ctx.bot.help_command if command.lower() == "help" else ctx.bot.get_command(command)
        if not command:
            return await ctx.send("Couldn't find command.")
        if isinstance(command.cog, Jishaku):
            return await ctx.send("<https://github.com/Gorialis/jishaku>")

        if isinstance(command, commands.HelpCommand):
            lines, starting_line_num = inspect.getsourcelines(type(command))
            filepath = f"{command.__module__.replace('.', '/')}.py"
        else:
            lines, starting_line_num = inspect.getsourcelines(command.callback.__code__)
            filepath = f"{command.callback.__module__.replace('.', '/')}.py"

        ending_line_num = starting_line_num + len(lines) - 1
        command = "help" if isinstance(command, commands.HelpCommand) else command
        embed = discord.Embed(
            title=f"Here is my source code for the `{command}` command.",
            description="Don't forget the license! (A star would also be appreciated ^^)",
            url=f"https://github.com/ItsArtemiz/RoUtils/blob/master/{filepath}#L{starting_line_num}-L{ending_line_num}",
            colour=ctx.bot.colour)
        await ctx.send(embed=embed)

def setup(bot:commands.Bot):
    bot.add_cog(Information(bot))