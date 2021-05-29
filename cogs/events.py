"""
Event Handling.

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

import discord
import random
import humanize

from discord.ext import commands

from bot import RoUtils
from datetime import datetime
from typing import List

from utils.logging import post_log
from utils.time import human_time

class Events(commands.Cog):
    def __init__(self, bot: RoUtils):
        self.bot = bot


    async def mod_nick(self, m:discord.Member) -> None:
        string = """abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!"#$%&'()*+,-./:;<=>?@[]^_`{|}~"""

        for l in m.display_name:
            if l in string:
                return
        else:
            try:
                await m.edit(nick='Moderated Nickname' + ''.join(random.sample(string.ascii_letters+string.digits, k=8)))
            except discord.HTTPException:
                pass

    @commands.Cog.listener()
    async def on_message_delete(self, message:discord.Message):
        if not message.guild: # Do not want to log DMs
            return

        if message.author.bot:
            return # Do not want to log bot messages.

        embed = discord.Embed(
            title = f"Message Deleted in #{message.channel}",
            description = f"Message: {message.channel.mention}",
            timestamp = datetime.utcnow(),
            colour = discord.Colour.red()
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
                value=', '.join(f'{a.filename} ({a.content_type})' for a in message.attachments)
            )

        embed.set_footer(text="Deleted At")
        embed.set_author(name=str(message.author), icon_url=message.author.avatar_url)

        await post_log(message.guild, name='bot-logs', embed=embed)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, L:List[discord.Message]):
        deleted = [m for m in L if len(m.content) <= 100]
        description = '\n'.join(f'**[{m.author}]:** {m.content}' for m in L if len(m.content)<=100)
        dummy = random.choice(L)

        embed = discord.Embed(
            title = f'{len(L)} messages deleted in #{dummy.channel}',
            timestamp = datetime.utcnow(),
            colour = discord.Colour.red(),
            description = description
        )

        embed.set_footer(text=f'{len(deleted)} messages are shown')
        try:
            await post_log(dummy.guild, name='bot-logs', embed=embed)
        except discord.HTTPException:
            await post_log(dummy.guild, name='bot-logs', content=f"{len(L)} messages were deleted in #{dummy.channel}. Cannot show messages, too long to send.")

    @commands.Cog.listener()
    async def on_message_edit(self, before:discord.Message, after:discord.Message):
        if not before.guild:
            return

        if before.author.bot:
            return

        if before.content != after.content:
            embed = discord.Embed(
                title = f'Message edited in #{before.channel}',
                colour = discord.Color.blue(),
                timestamp = datetime.utcnow(),
                description = f'Channel: {before.channel.mention} | [Message]({after.jump_url})'
            )
            embed.set_footer(text='Edited At')

            embed.add_field(name='Before', value=before.content, inline=False)
            embed.add_field(name='After', value=after.content, inline=False)

            embed.set_author(name=str(after.author), icon_url=after.author.avatar_url)

            await post_log(after.guild, name='bot-logs', embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member:discord.Member):
        embed = discord.Embed(
            title = 'Member Joined',
            description = f'{member.mention} {humanize.intcomma(humanize.ordinal(len(member.guild.members)))} to join.\n'\
                          f'created {human_time(member.created_at - datetime.utcnow(), minimum_unit="minutes")}.',
            colour = discord.Colour.green(),
            timestamp = datetime.utcnow()
        )
        embed.set_footer(text='Joined At')
        embed.set_author(name=str(member), icon_url=member.avatar_url)

        await post_log(member.guild, name='bot-logs', embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member:discord.Member):
        embed = discord.Embed(
            title = 'Member Left',
            colour = discord.Colour.red(),
            description = f'{member.mention} joined {human_time(member.joined_at - datetime.utcnow())}.',
            timestamp = datetime.utcnow()
        )

        embed.set_footer(text=f'ID: {member.id}')
        embed.set_author(name=str(member), icon_url=member.avatar_url)

        roles = member.roles
        roles.remove(member.guild.default_role)

        if roles:
            embed.add_field(name='Roles', value=''.join(r.mention for r in roles))

        await post_log(member.guild, name='bot-logs', embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before:discord.Member, after:discord.Member):
        if before.bot:
            return

        if before.display_name != after.display_name:

            embed = discord.Embed(
                title = 'Member Nickname Update',
                colour = discord.Colour.blue(),
                timestamp = datetime.utcnow(),
                description = f'**Before:** {before.display_name}\n**After:** {after.display_name}'
            )

            embed.set_footer(text='Updated At')
            embed.set_author(name=str(after), icon_url=after.avatar_url)

            await post_log(after.guild, name='bot-logs', embed=embed)
            await self.mod_nick(after)

        if before.roles != after.roles:
            embed = discord.Embed(
                title = 'Member Roles Updated',
                colour = discord.Colour.blue(),
                timestamp = datetime.utcnow(),
            )
            embed.set_author(name=str(after), icon_url=after.avatar_url)
            

            temp = list(set(before.roles + after.roles))
            added = []
            removed = []

            for role in temp:
                if role in before.roles and role not in after.roles:
                    removed.append(role)
                elif role in after.roles and role not in before.roles:
                    added.append(role)

            if added:
                embed.add_field(name="Roles Added", value=", ".join([r.mention for r in added]), inline=False)
            if removed:
                embed.add_field(name="Roles Removed", value=", ".join([r.mention for r in removed]), inline=False)

            await post_log(guild=after.guild, name="bot-logs", embed=embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        async for entry in guild.audit_logs(action=discord.AuditLogAction.ban):
            entry: discord.AuditLogEntry = entry
            if entry.target.id == user.id:
                reason = f"**Reason:** {entry.reason if entry.reason else 'No reason was provided.'}\n"\
                         f"**Moderator:** {entry.user.mention} (ID: `{entry.user.id}`)"
                break

        embed = discord.Embed(
            title = 'Member Banned',
            description = reason,
            colour = discord.Colour.dark_red(),
            timestamp = datetime.utcnow()
        )

        embed.set_author(name=str(user), icon_url=user.avatar_url)

        await post_log(guild=guild, name="bot-logs", embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild:discord, user:discord.User):
        async for entry in guild.audit_logs(action=discord.AuditLogAction.unban):
            entry: discord.AuditLogEntry = entry
            if entry.target.id == user.id:
                reason = f"**Reason: ** {entry.reason if entry.reason else 'No reason provided.'}\n"\
                         f" **Moderator: ** {entry.user.mention} (ID: `{entry.user.id}`)"
                break

        embed = discord.Embed(
            title = 'Member Unbanned',
            description = reason,
            colour = discord.Colour.green(),
            timestamp = datetime.utcnow()
        )

        embed.set_author(name=str(user), icon_url=user.avatar_url)

        await post_log(guild=guild, name="bot-logs", embed=embed)

        await post_log(guild=guild, name="bot-logs", embed=embed)

def setup(bot:RoUtils):
    bot.add_cog(Events(bot))
