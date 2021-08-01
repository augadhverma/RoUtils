"""
The API module - To work with various APIs and give the raw output.
Copyright (C) 2021  Augadh Verma

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from __future__ import annotations

import discord
import aiohttp
import utils
import json

from discord.ext import commands
from typing import Optional
from utils import Context, Bot
from jishaku.paginators import PaginatorEmbedInterface

GROUP = 'https://groups.roblox.com/v1/groups'
GROUPV2 = 'https://groups.roblox.com/v2'

class API(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def send_paginator(self, ctx: Context, content: str, send_to: discord.abc.Messageable = None):
        send_to = send_to or ctx
        paginator = commands.Paginator(prefix='```json\n', max_size=800, linesep='\n')

        for data in content.split('\n'):
            paginator.add_line(data)

        embed = discord.Embed(colour=ctx.colour)

        interface = PaginatorEmbedInterface(self.bot, paginator, owner=ctx.author, embed=embed)
        await interface.send_to(send_to)

    @utils.is_bot_channel()
    @commands.command(aliases=['msgraw'])
    async def rawmsg(self, ctx: Context, message: Optional[str]):
        """Gets the raw contents of the message.
        
        You need to invoke the command in the same channel where the message is
        else you will need to provide the channel id as well.
        
        Usage:
        • Using only message id: `msgraw messageId`
        • Using channel and message id: `msgraw channelId-messageId`
        """
        if ctx.replied_reference:
            channel = ctx.replied_reference.channel_id
            msg = ctx.replied_reference.message_id
        else:
            if message is None:
                return await ctx.send('Please give a message id.')
            try:
                channel, msg = message.split('-')
            except ValueError:
                channel = ctx.channel.id
                msg = message

            try:
                channel = int(channel)
                msg = int(msg)
            except Exception as e:
                return await ctx.send(e)

        try:
            r = await self.bot.http.get_message(channel, msg)
        except Exception as e:
            return await ctx.send(e)
        else:
            data = json.dumps(r, indent=4)
            
            await self.send_paginator(ctx, data, ctx)

    async def json_content(self, url: str) -> str:
        r = await self.bot.session.get(url)
        
        data = json.dumps(await r.json(), indent=4)
        return data

    @utils.is_bot_channel()
    @commands.group(invoke_without_command=True)
    async def raw(self, ctx: Context, *, url: str):
        """Gives a raw-json formated version of a request."""
        try:
            content = await self.json_content(url)
        except aiohttp.InvalidURL:
            return await ctx.send('Invalid url given.')

        await self.send_paginator(ctx, content)

    @utils.is_bot_channel()
    @raw.command(usage='<group id>')
    async def roles(self, ctx: Context, *, group: int):
        """Gives a raw-json formated version of a Roblox Group's Roles.
        
        An easy way to check for ranks of a group.
        """
        
        content = await self.json_content(f'{GROUP}/{group}/roles')
        await self.send_paginator(ctx, content)

    @utils.is_bot_channel()
    @raw.command(usage='<group id>')
    async def group(self, ctx: Context, *, group: int):
        """Shows a raw-json formated version of a Roblox Group."""

        content = await self.json_content(f'{GROUP}/{group}')
        await self.send_paginator(ctx, content)

    @utils.is_bot_channel()
    @raw.command(usage='<user id>')
    async def user(self, ctx: Context, *, user: int):
        """Shows a raw-json formated version of a Roblox User."""
        content = await self.json_content(f'https://users.roblox.com/v1/users/{user}')
        await self.send_paginator(ctx, content)

    @utils.is_bot_channel()
    @raw.command(usage='<user id>', name='user-roles')
    async def user_roles(self, ctx: Context, *, user: int):
        """Shows a raw-json formatted version of a Roblox User's Group Roles.
        
        If you want check if a user is in a group and check their rank in the group,
        consider using the `uig` or `useringroup` command.
        """
        content = await self.json_content(f'{GROUPV2}/users/{user}/groups/roles')
        await self.send_paginator(ctx, content)
        
def setup(bot: Bot):
    bot.add_cog(API(bot))