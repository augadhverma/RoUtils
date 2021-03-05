from typing import Iterable, Optional, Union
import discord
from discord.ext import commands
from discord.utils import get

from utils.classes import EmbedLog
from datetime import datetime

BOT_COMMANDS = (
    "!verify",
    "!update",
    "!getroles",
    "!reverify",
    "!premium",
    "!help",
    "t!rank",
    "t!help",
    "?help",
    "?rank",
    "?suggest"
)

class MemberLogs:
    def __init__(self, embed:discord.Embed, iterable:Iterable) -> None:
        self.embed = embed
        self.iterable = iterable

    async def post_log(self, channel:discord.TextChannel=None) -> Optional[discord.Message]:
        channel = channel or get(self.iterable, name="bot-logs")
        if channel:
            try:
                return await channel.send(embed=self.embed)
            except:
                pass

class ModEvents(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_delete(self, message:discord.Message):
        if not message.guild:
            return
        if message.author.bot:
            return
        embed = discord.Embed(
            title = "Message Deleted",
            timestamp = datetime.utcnow(),
            description = f"Deleted in {message.channel.mention}",
            colour = discord.Colour.red()
        )
        embed.add_field(
            name = "Content",
            value = message.content
        )
        embed.set_footer(text="Deleted At")
        embed.set_author(name=str(message.author), icon_url=message.author.avatar_url)

        await MemberLogs(embed, message.guild.text_channels).post_log()

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages:list):
        deleted = []
        description = ""
        sample = None
        for msg in messages:
            if len(msg.content) > 100:
                pass
            description += f"**[{msg.author}]:** {msg.content}\n"
            deleted.append(msg)
            sample:discord.Message = msg
        embed = discord.Embed(
            title = f"{len(messages)} Messages deleted in #{sample.channel.name}",
            timestamp = datetime.utcnow(),
            description = description,
            colour = discord.Color.red()
        )
        embed.set_footer(text=f"{len(deleted)} messages shown")

        await MemberLogs(embed, sample.guild.text_channels).post_log()


    @commands.Cog.listener()
    async def on_message_edit(self, before:discord.Message, after:discord.Message):
        if not before.guild:
            return
        if before.content == after.content:
            return
        embed = discord.Embed(
            title = "Message Edited",
            colour = discord.Color.blue(),
            timestamp = datetime.utcnow(),
            description = f"Edited in {after.channel.mention} | [Message]({after.jump_url})"
        )
        embed.set_footer(text="Modified At")
        embed.add_field(
            name="Before",
            value=before.content,
            inline=False
        )
        embed.add_field(
            name="After",
            value = after.content,
            inline=False
        )
        embed.set_author(name=str(after.author),icon_url=after.author.avatar_url)

        await MemberLogs(embed, after.guild.text_channels).post_log()



    @commands.Cog.listener()
    async def on_member_join(self, member:discord.Member):
        embed = discord.Embed(
            title="Member Joined",
            colour = discord.Colour.green(),
            timestamp = datetime.utcnow()
        )
        embed.set_author(name=str(member), icon_url=member.avatar_url, url=member.avatar_url)
        embed.set_footer(text=f"ID: {member.id}")
        description = f"{member.mention}'s account {datetime.strftime(member.created_at, 'was created on %A %d, %B of %Y at %H:%M %p')}\n*New server member count: {member.guild.member_count}*"
        embed.description = description
        await MemberLogs(embed, member.guild.text_channels).post_log()

    async def kicked_event(self, member:discord.Member, entry:discord.AuditLogEntry) -> Optional[discord.Message]:
        embed = discord.Embed(
            title = "Member Kicked",
            colour = discord.Colour.red(),
            timestamp = datetime.utcnow()
        )

        embed.set_thumbnail(url=member.avatar_url)
        embed.set_footer(text=self.bot.footer)
        embed.description=f"**Offender:** {entry.target.mention} `({entry.target.id})`\n**Reason:** {entry.reason}\n**Moderator:** {entry.user.mention} `({entry.user.id})`"

        return await MemberLogs(embed, member.guild.text_channels).post_log()

    @commands.Cog.listener()
    async def on_member_remove(self, member:discord.Member):
        embed = discord.Embed(
            title = "Member Left",
            colour = discord.Color.red(),
            timestamp = datetime.utcnow()
        )

        embed.set_author(name=str(member), icon_url=member.avatar_url, url=member.avatar_url)
        embed.set_footer(text=f"ID: {member.id}")
        embed.description = f"{member.mention} {datetime.strftime(member.joined_at, 'joined us on %A %d, %B of %Y at %H:%M %p')}\n*New server member count: {member.guild.member_count}*"

        roles = member.roles
        roles.remove(member.guild.default_role)
        if member.roles:
            embed.add_field(
                name = "Roles",
                value = ", ".join([role.mention for role in roles])
            )
        await MemberLogs(embed, member.guild.text_channels).post_log()

        async for entry in member.guild.audit_logs(action=discord.AuditLogAction.kick, limit=1):
            entry:discord.AuditLogEntry = entry
            if entry.target.id == member.id:
                if entry.user.id == self.bot.user.id:
                    break
                else:
                    await self.kicked_event(member, entry)
    @commands.Cog.listener()
    async def on_member_ban(self, guild:discord.Guild, user:Union[discord.User, discord.Member]):
        async for entry in guild.audit_logs(action=discord.AuditLogAction.ban):
            entry:discord.AuditLogEntry = entry
            if entry.target.id == user.id:
                if entry.user.id == self.bot.user.id:
                    return
                else:
                    embed = discord.Embed(
                        title = "Member Banned",
                        colour = discord.Color.dark_red(),
                        timestamp = datetime.utcnow()
                    )
                    embed.set_thumbnail(url=user.avatar_url)
                    embed.set_footer(text=self.bot.footer)
                    embed.description=f"**Offender:** {entry.target.mention} `({entry.target.id})`\n**Reason:** {entry.reason}\n**Moderator:** {entry.user.mention} `({entry.user.id})`"

                    return await MemberLogs(embed, guild.text_channels).post_log()

    @commands.Cog.listener()
    async def on_member_unban(self, guild:discord.Guild, user:discord.User):
        async for entry in guild.audit_logs(action=discord.AuditLogAction.unban):
            entry:discord.AuditLogEntry = entry
            if entry.target.id == user.id:
                if entry.user.id == self.bot.user.id:
                    return
                else:
                    embed = discord.Embed(
                        title = "Member Unbanned",
                        colour = discord.Color.green(),
                        timestamp = datetime.utcnow()
                    )
                    embed.set_thumbnail(url=user.avatar_url)
                    embed.set_footer(text=self.bot.footer)
                    embed.description=f"**User unbanned:** {entry.target.mention} `({entry.target.id})`\n**Reason:** {entry.reason}\n**Moderator:** {entry.user.mention} `({entry.user.id})`"

                    return await MemberLogs(embed, guild.text_channels).post_log()

    @commands.Cog.listener()
    async def on_member_update(self, before:discord.Member, after:discord.Member):
        if before.bot:
            return
        
        if before.nick != after.nick:
            embed = discord.Embed(
                title = "Nickname Changed",
                colour = discord.Colour.blue(),
                timestamp = datetime.utcnow()
            )
            embed.set_footer(text="Updated At")
            embed.set_author(name=str(before), icon_url=before.avatar_url)
            embed.description = f"**Before:** {before.nick}\n**After:** {after.nick}"

            await MemberLogs(embed, after.guild.text_channels).post_log()

        if before.roles != after.roles:
            embed = discord.Embed(
                title = "Member Roles Updated",
                colour = discord.Color.blue(),
                timestamp = datetime.utcnow()
            )
            embed.set_footer(text="Updated At")
            embed.set_author(name=str(before), icon_url=before.avatar_url)
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

            await MemberLogs(embed, after.guild.text_channels).post_log()

    @commands.Cog.listener()
    async def on_message(self, message:discord.Message):
        if str(message.channel.id) not in ("671616323696197647","706012467444056125"):
            return
        cmds = self.bot.commands
        content:str = message.content.lower()
        if content.startswith(BOT_COMMANDS):
            return await message.channel.send(f"{message.author.mention} Whoops! Make sure you use bot commands in <#678198477108543518>, they will not work here.", delete_after=5.0)


def setup(bot:commands.Bot):
    bot.add_cog(ModEvents(bot))