"""
Applications Module - A way we can now discuss about Staff Applications.
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

from discord.ext import commands
from utils import Bot, Context

APPLICATIONS = 862654466527199242
WEBHOOKID = 862654541933576223

COUNCIL = 626860276045840385
MANAGEMENT = 671634821323423754

class Apps(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.channel.id == APPLICATIONS:
            return

        if message.embeds and message.author.id == WEBHOOKID:
            embed = message.embeds[0]
            thread = await message.channel.create_thread(
                name=embed.title,
                message=message,
                reason=f'New Application {embed.title.split()[-1]} just arrived',
                type=discord.ChannelType.private_thread
            )

            for m in message.guild.members:
                if m.top_role.id in (COUNCIL, MANAGEMENT):
                    await thread.add_user(m)

    @commands.Cog.listener()
    async def on_thread_delete(self, thread: discord.Thread):
        if not thread.parent_id == APPLICATIONS:
            return

        channel = thread.parent or self.bot.get_channel(APPLICATIONS)
        message = channel.get_partial_message(thread.id)

        if message is None:
            try:
                message = await channel.fetch_message(thread.id)
            except discord.HTTPException:
                return

        await message.add_reaction('\U00002705')
    
    @commands.Cog.listener()
    async def on_thread_update(self, before: discord.Thread, after: discord.Thread):
        thread = before
        if not thread.parent_id == APPLICATIONS:
            return

        channel = thread.parent or self.bot.get_channel(APPLICATIONS)

        try:
            message = await channel.fetch_message(thread.id)
        except discord.HTTPException:
            return

        ctx = await self.bot.get_context(message, cls=Context)
        await ctx.tick(None)

def setup(bot: Bot):
    bot.add_cog(Apps(bot))