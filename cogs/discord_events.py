"""
Logs various discord events.
Copyright (C) 2021-present ItsArtemiz (Augadh Verma)

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

import discord
from discord.ext import commands

from utils import Bot, Context, Embed, format_dt

class DiscordEvents(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot:
            return
        
        ctx = await self.bot.get_context(message, cls=Context)
        if ctx.valid:
            return

        embed = Embed(
            bot=self.bot,
            title=f"Message Deleted in #{message.channel}",
            footer="Deleted At",
            colour=discord.Colour.red()
        )
        embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)

        if message.content:
            embed.add_field(
                name="Content",
                value=message.content,
                inline=False
            )
        if message.attachments:
            embed.add_field(
                name="Attachments",
                value=', '.join(f'{a.filename} ({a.content_type})' for a in message.attachments),
                inline=False
            )
        await self.bot.post_log(message.guild, 'message', embed=embed)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: list[discord.Message]) -> None:
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

        await self.bot.post_log(dummy.guild, 'message', embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if before.guild is None or before.author.bot:
            return

        if before.content != after.content:
            embed = Embed(
                bot=self.bot,
                title=f"Message edited in #{before.channel}",
                description=f"Channel: {before.channel.mention} | [Message]({after.jump_url})",
                footer="Edited At"
            )
            embed.set_author(name=str(before.author), icon_url=before.author.display_avatar.url)

            embed.add_field(name="Before", value=before.content, inline=False)
            embed.add_field(name="After", value=after.content, inline=False)

            await self.bot.post_log(before.guild, 'message', embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        embed = Embed(
            title="Member Joined",
            colour=discord.Colour.green(),
            description=f"{member.mention} {format(len(member.guild.members), ',')} to join.\n"\
                        f"Created: {format_dt(member.created_at)}",
            footer=f"ID: {member.id} | Joined At",
            bot=self.bot
        )
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)

        await self.bot.post_log(member.guild, 'bot', embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        embed = Embed(
            bot=self.bot,
            title="Member Left",
            description=f"{member.mention} joined at {format_dt(member.joined_at)}",
            footer=f"ID: {member.id} | Left At",
            colour=discord.Colour.red()
        )
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)

        roles = member.roles
        roles.remove(member.guild.default_role)
        if roles:
            embed.add_field(
                name="Roles",
                value=", ".join(r.mention for r in roles),
                inline=False
            )
        await self.bot.post_log(member.guild, 'bot', embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        if before.display_name != after.display_name:
            embed = Embed(
                bot=self.bot,
                title="Nickname Update",
                description=f"**Before:** {before.display_name}\n**After:** {after.display_name}",
                footer="Updated At"
            )
            embed.set_author(name=str(after), icon_url=after.display_avatar.url)
            await self.bot.post_log(before.guild, 'bot', embed=embed)

        if before.roles != after.roles:
            embed = Embed(
                bot=self.bot,
                title="Roles Update",
                footer="Updated At"
            )
            embed.set_author(name=str(after), icon_url=after.display_avatar.url)

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

            await self.bot.post_log(after.guild, 'bot', embed=embed)

        if before.is_timed_out() != after.is_timed_out():
            if before.is_timed_out() and not after.is_timed_out():
                action = "Removed"
                timeout = None
            else:
                action = "Added"
                timeout = after.timed_out_until
            embed = Embed(
                bot=self.bot,
                title=f"Timeout {action}",
                footer="Action At"
            )
            embed.set_author(name=str(after), icon_url=after.display_avatar.url)

            if timeout:
                embed.description = f"Timeout Until: {format_dt(timeout)}"
            
            await self.bot.post_log(after.guild, 'bot', embed=embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User) -> None:
        ban = await guild.fetch_ban(user)
        embed = Embed(
            bot=self.bot,
            title="Member Banned",
            description=ban.reason if ban.reason else "No reason provided.",
            colour=discord.Colour.dark_red()
        )
        embed.set_author(name=str(user), icon_url=user.display_avatar.url)

        await self.bot.post_log(guild, 'bot', embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User) -> None:
        ban = await guild.fetch_ban(user)

        embed = Embed(
            bot=self.bot,
            title="Member Unbanned",
            description=f"Previously banned for:\n{ban.reason if ban.reason else 'No reason provided'}",
            footer="Unbanned at",
            colour=discord.Colour.green()
        )
        embed.set_author(name=str(user), icon_url=user.display_avatar.url)

        await self.bot.post_log(guild, 'bot', embed=embed)

async def setup(bot: Bot) -> None:
    await bot.add_cog(DiscordEvents(bot))
