import asyncio
import discord

from typing import Optional, Union
from datetime import datetime
from collections import Counter

from discord.ext import commands, menus
from discord.utils import escape_markdown

from utils.db import Connection
from utils.checks import COUNCIL, MANAGEMENT, staff, council
from utils.cache import Cache
from utils.classes import TagPages

mentions = discord.AllowedMentions(
    everyone=False,
    users=False,
    roles=False
)

ADMINS = (449897807936225290, 173977882765426688, 311395138133950465, 604031762359910404, 621777717037105173)

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

    async def get_or_fetch_user(self, id:int):
        user = self.bot.get_user(id)
        if user:
            return user
        user = self.bot.fetch_user(id)
        return user


    async def get_tag(self, name:str) -> Union[str, None]:
        tag = await self.tag_db.find_one({'name':name})
        if tag:
            await self.tag_db.update_one({'name':name},{"$set":{"uses":tag['uses']+1}})
            return tag['content']
        return None

    async def create_tag(self, user:discord.Member,name:str, content:str) -> bool:
        created = datetime.utcnow()
        document = {
            "owner":user.id,
            "name":name,
            "content":content,
            "id":created.microsecond,
            "uses":0,
            "created":created
        }
        tag = await self.tag_db.insert_one(document)
        return tag.acknowledged

    async def delete_tag(self, ctx:commands.Context, user:discord.Member, name:str) -> None:
        tag = await self.tag_db.find_one({'name':name})
        if tag:
            if tag['owner'] == user.id:
                await self.tag_db.delete_one({'name':name})
                await ctx.send("Successfully deleted the tag \U0001f44c")
            elif tag['owner'] in ADMINS:
                await ctx.send("Can't delete a tag made by an other Admin/Council Member.")
            elif (MANAGEMENT in [role.id for role in ctx.author.roles] or COUNCIL in [role.id for role in ctx.author.roles]):
                await self.tag_db.delete_one({'name':name})
                await ctx.send("Successfully deleted the tag \U0001f44c")
            elif await self.bot.is_owner(ctx.author):
                await self.tag_db.delete_one({'name':name})
                await ctx.send("Successfully deleted the tag \U0001f44c")
            else:
                await ctx.send(f"You are not the owner of the tag **{name}**")
        else:
            await ctx.send(f"Cannot find tag **{name}**.")
        

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
    @tag.command(aliases=['add','+', 'new'])
    async def create(self, ctx:commands.Context,name:str,*,content:commands.clean_content):
        """Creates a new tag"""
        cmds = ctx.command.parent.commands
        for cmd in cmds:
            if name == cmd.name:
                return await ctx.send(f"**{name}** is a reserved keyword and cannot be used to make a new tag.")
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
    @tag.command(aliases=['remove','-'])
    async def delete(self, ctx:commands.Context, *,name:str):
        """Deletes a tag"""
        await self.delete_tag(ctx, ctx.author, name)

    @staff()
    @tag.command()
    async def raw(self, ctx:commands.Context, *,name:str):
        """Shows the raw data of a tag"""

        tag = await self.get_tag(name)
        if not tag:
            await ctx.send(f"Tag **{name}** not found.")
        else:
            await ctx.send(content=escape_markdown(tag))

    @staff()
    @tag.command(aliases=['update'])
    async def edit(self, ctx:commands.Context, name:str, *,content:str):
        """Updates an existing tag"""

        tag = await self.tag_db.find_one({'name':name})
        if tag:
            if tag['owner'] == ctx.author.id:
                await self.tag_db.update_one({'name':name},{"$set":{'content':content}})
                await ctx.send("Successfully updated the tag \U0001f44c")
            else:
                await ctx.send("You can't edit someone elses tag.")
        else:
            await ctx.send(f"Unable to find tag **{name}**.")

    @staff()
    @tag.command()
    async def info(self, ctx:commands.Context, *,name:str):
        """Shows info about a tag"""
        tag = await self.tag_db.find_one({'name':name})
        if not tag:
            return await ctx.send(f"Could not find the tag {name}")
        user:discord.User = await self.get_or_fetch_user(tag['owner'])

        embed = discord.Embed(
            colour = self.bot.colour,
            timestamp=tag['created'],
            title=f"{name} (ID: {tag['id']})"
        )
        embed.set_footer(text="Tag Created At")
        embed.set_author(name=user.name, icon_url=user.avatar_url)
        embed.add_field(name="Owner", value=user.mention)
        embed.add_field(name="Uses", value=tag['uses'])

        await ctx.send(embed=embed)

    @staff()
    @tag.command(name="list", aliases=['all'])
    async def _list(self, ctx:commands.Context, user:Optional[discord.User]):
        """Shows all the registered tags"""
        a = []
        if not user:
            tags = self.tag_db.find({})
        else:
            tags = self.tag_db.find({'owner':user.id})
        async for t in tags:
            a.append(t)

        if not len(a):
            return await ctx.send("There are no tags.")

        menu = menus.MenuPages(source=TagPages(entries=a, per_page=20))
        await menu.start(ctx)

    @staff()
    @commands.command()
    async def tags(self, ctx:commands.Context, user:Optional[discord.User]):
        """Shows all the registered tags
        
        An alias for `tag list`"""
        a = []
        if not user:
            tags = self.tag_db.find({})
        else:
            tags = self.tag_db.find({'owner':user.id})
        async for t in tags:
            a.append(t)

        if not len(a):
            return await ctx.send("There are no tags.")

        menu = menus.MenuPages(source=TagPages(entries=a, per_page=20))
        await menu.start(ctx)




        


def setup(bot:commands.Bot):
    bot.add_cog(Tags(bot))