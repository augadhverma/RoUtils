import discord

from typing import Union

from discord.ext import commands, menus
from discord.utils import escape_mentions, escape_markdown
from datetime import datetime

from utils.db import Connection
from utils.checks import staff
from utils.cache import Cache, CacheType

mentions = discord.AllowedMentions(
    everyone=False,
    users=False,
    roles=False
)

class Paginator(menus.ListPageSource):
    def __init__(self, data, title, colour, footer):
        self.title= title
        self.colour = colour
        self.footer = footer
        super().__init__(data, per_page=5)

    async def format_page(self, menu, data):
        embed = discord.Embed(
            title=self.title,
            colour=self.colour,
            timestamp=datetime.utcnow(),
            description = "\n".join(item for item in data)
        )
        embed.set_footer(text=self.footer)
        return embed

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

    async def delete_tag(self, ctx:commands.Context, user:discord.Member, name:str) -> None:
        tag = await self.tag_db.find_one({'name':name})
        if tag:
            if tag['owner'] == user.id:
                await self.tag_db.delete_one({'name':name})
                await ctx.send("Successfully deleted the tag \U0001f44c")
            else:
                await ctx.send("You are not the owner of the tag **{name}**")
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
    @tag.command()
    async def edit(self, ctx:commands.Context, name:str, *,content:str):
        """Updates an existing tag"""

        tag = await self.tag_db.find_one({'name':name})
        if tag:
            if tag['owner'] == ctx.author.id:
                await self.tag_db.update_one({'name':name},{'content':content})
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
            timestamp=datetime.utcnow(),
            title=name
        )
        embed.set_footer(text=self.bot.footer)
        embed.set_author(name=user.name, icon_url=user.avatar_url)
        embed.description = f"The tag is {len(tag['content'])} characters long and has been sent to you in DMs."

        await ctx.send(embed=embed)
        await ctx.author.send(tag['content'])

    @staff()
    @tag.command(name="list")
    async def _list(self, ctx:commands.Context):
        """Shows all the registered tags"""
        tags = []
        data = self.tag_db.find({})
        async for x in data:
            tags.append(x['name'])
        menu = menus.MenuPages(source=Paginator(tags, "All Tags", self.bot.colour, self.bot.footer))
        await menu.start(ctx)





        


def setup(bot:commands.Bot):
    bot.add_cog(Tags(bot))