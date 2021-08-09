"""
The Logging Module - Logs various dpy events.
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

from typing import List

from utils import Bot, Context, Embed, utcnow, format_date

class Logs(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.guild is None:
            return

        if message.author.bot:
            return

        ctx = await self.bot.get_context(message, cls=Context)
        if ctx.valid:
            return

        embed = Embed(
            title=f'Message Deleted in #{message.channel}',
            description=f'Channel: {message.channel.mention}',
            author=message.author,
            footer='Deleted At',
            timestamp=utcnow(),
            colour=discord.Colour.red()
        )

        if message.content:
            embed.add_field(
                name='Content',
                value=message.content,
                inline=False
            )

        if message.attachments:
            embed.add_field(
                name='Attachments',
                value=', '.join(f'{a.filename} ({a.content_type})' for a in message.attachments),
                inline=False
            )

        await embed.post_log(self.bot, message.guild)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: List[discord.Message]):

        deleted = [m for m in messages if len(m.content) <= 200]
        description = '\n'.join(f'**[{m.author}]:** {m.content}' for m in deleted)
        dummy = messages[0]
               
        if len(description) > 2048:
            description = f'Too many messages to show. {len(messages)} messages were deleted'
        
        embed = Embed(
            title = f'{len(messages)} messages deleted in #{dummy.channel}',
            colour = discord.Colour.red(),
            description = description,
            footer = f'{len(deleted)} messages are shown.'
        )
        
        await embed.post_log(self.bot, dummy.guild)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.guild is None:
            return

        if before.author.bot:
            return

        if before.content != after.content:
            embed = Embed(
                title=f'Message Edited in #{before.channel}',
                colour=discord.Colour.blue(),
                timestamp=utcnow(),
                description = f'Channel: {before.channel.mention} | [Message]({after.jump_url})',
                author=before.author,
                footer='Edited At'
            )

            embed.add_field(name='Before', value=before.content, inline=False)
            embed.add_field(name='After', value=after.content, inline=False)

            await embed.post_log(self.bot, before.guild)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        embed = Embed(
            title='Member Joined',
            colour=discord.Colour.green(),
            timestamp=utcnow(),
            description=f'{member.mention} {format(len(member.guild.members), ",")} to join.\n'\
                        f'Created: {format_date(member.created_at)}',
            author=member,
            footer=f'ID: {member.id} | Joined At'
        )

        await embed.post_log(self.bot, member.guild)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        embed = Embed(
            title='Member Left',
            colour=discord.Colour.red(),
            timestamp=utcnow(),
            description=f'{member.mention} joined {format_date(member.joined_at)}',
            author=member,
            footer=f'ID: {member.id}'
        )

        await embed.post_log(self.bot, member.guild)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.bot:
            return
        
        if before.display_name != after.display_name:
            embed = Embed(
                title='Nickname Update',
                colour=discord.Colour.blue(),
                timestamp=utcnow(),
                description=f'**Before:** {before.display_name}\n**After:** {after.display_name}',
                footer='Updated At',
                author=after
            )

            await embed.post_log(self.bot, before.guild)

        if before.roles != after.roles:
            embed = Embed(
                title='Roles Updated',
                colour=discord.Colour.blue(),
                timestamp=utcnow(),
                author=after,
                footer='Updated At'
            )

            temp = list(set(before.roles + after.roles))
            added = []
            removed = []

            for role in temp:
                if role in before.roles and role not in after.roles:
                    removed.append(role)
                elif role in after.roles and role not in before.roles:
                    added.append(role)

            if added:
                embed.add_field(name='Roles Added', value=', '.join([r.mention for r in added]), inline=False)
            if removed:
                embed.add_field(name='Roles Removed', value=', '.join([r.mention for r in removed]), inline=False)

            await embed.post_log(self.bot, before.guild)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        ban = await guild.fetch_ban(user)

        embed = Embed(
            title='Member Banned',
            description=ban.reason if ban.reason else 'No reason provided',
            author=user,
            footer='Banned at',
            timestamp=utcnow(),
            colour=discord.Colour.dark_red()
        )

        await embed.post_log(self.bot, guild)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        ban = await guild.fetch_ban(user)

        embed = Embed(
            title='Member UnBanned',
            description=f'Previously Banned for:\n{ban.reason if ban.reason else "No reason provided"}',
            author=user,
            footer='Unbanned at',
            timestamp=utcnow(),
            colour=discord.Colour.green()
        )

        await embed.post_log(self.bot, guild)

def setup(bot: Bot):
    bot.add_cog(Logs(bot))