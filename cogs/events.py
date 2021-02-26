import discord
from discord.ext import commands

from utils.classes import EmbedLog
from datetime import datetime

class ModEvents(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot

    async def get_message_logs(self):
        pass

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

        await EmbedLog(await self.bot.get_context(message), embed).post_log()

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

        await EmbedLog(await self.bot.get_context(sample), embed).post_log()

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

        await EmbedLog(await self.bot.get_context(before), embed).post_log()


    @commands.Cog.listener()
    async def on_member_join(self, member:discord.Member):
        embed = discord.Embed(
            title="Member Joined",
            colour = discord.Colour.green(),
            timestamp = datetime.utcnow()
        )
        embed.set_author(name=str(member), icon_url=member.avatar_url)
        embed.set_footer(text=f"ID: {member.id}")
        embed.description = f""


def setup(bot:commands.Bot):
    bot.add_cog(ModEvents(bot))