import discord

from typing import Union

from discord.ext import commands
from discord.utils import escape_mentions

from utils.db import Connection
from utils.checks import staff
from utils.cache import Cache, CacheType

mentions = discord.AllowedMentions(
    everyone=False,
    users=False,
    roles=False
)

class Tags(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        self.cache = Cache()
        self.tag_db = Connection("Utilities","Tags")

    def replied_reference(self, message):
        ref = message.reference
        if ref and isinstance(ref.resolved, discord.Message):
            return ref.resolved.to_reference()
        return None


    async def get_tag(self, name:str) -> Union[str, None]:
        exist = self.cache.get(CacheType.Tag, name)
        if exist:
            return exist
        tag = await self.tag_db.find_one({'name':name.lower()})
        if tag:
            self.cache.set(CacheType.Tag, name, tag['content'])
            return tag['content']
        return None

    async def create_tag(self, user:discord.Member,name:str, content:str) -> bool:
        document = {
            "owner":user.id,
            "name":name,
            "content":escape_mentions(content)
        }
        tag = await self.tag_db.insert_one(document)
        return tag.acknowledged

    async def delete_tag(self, user:discord.Member, name:str) -> bool:
        tag = await self.tag_db.find_one({'name':name})
        if tag:
            if tag['owner'] == user.id:
                deleted = await self.tag_db.delete_one({'name':name})
                return deleted.acknowledged
        return False
        

    @staff()
    @commands.group(invoke_without_command=True)
    async def tag(self, ctx:commands.Context,*,name:str):
        """Gets the tag from the database"""
        tag = await self.get_tag(name)
        if tag:
            await ctx.send(content=tag, allowed_mentions=mentions, reference=self.replied_reference(ctx.message))
        else:
            await ctx.send(f"Tag **{name}** not found.")

    @staff()
    @tag.command()
    async def create(self, ctx:commands.Context,name:str,*,content:str):
        """Creates a new tag"""
        tag = await self.get_tag(name)
        if tag:
            await ctx.send(f"Tag **{name}** already exists.")
            return

        tag = await self.create_tag(ctx.author, name, content)
        if tag:
            await ctx.send(f"Tag **{name}** succesfully created \U0001f44c")
        else:
            await ctx.send("Unable to create tag at the moment.")

    @staff()
    @tag.command()
    async def delete(self, ctx:commands.Context, *,name:str):
        """Deletes a tag"""
        tag = await self.delete_tag(ctx.author, name)


def setup(bot:commands.Bot):
    bot.add_cog(Tags(bot))