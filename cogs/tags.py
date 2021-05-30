"""
Tags and stuff.

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

from discord.ext import commands, menus
from bot import RoUtils
from datetime import datetime

from typing import Optional
from utils.paginator import TagPages, jskpagination
from utils.db import MongoClient
from utils.checks import admin, botchannel
from utils.utils import TagEntry, TagNotFound

from difflib import get_close_matches

ADMINS = (449897807936225290, 173977882765426688, 311395138133950465, 604031762359910404, 621777717037105173)

class Tags(commands.Cog):
    def __init__(self, bot:RoUtils):
        self.bot = bot
        self._cache = dict()
        self.db = bot.tag_db

    def replied_reference(self, message):
        ref = message.reference
        if ref and isinstance(ref.resolved, discord.Message):
            return ref.resolved.to_reference()
        return None

    async def get_tag(self, name:str, update_uses=False) -> TagEntry:
        tag = self._cache.get(name, None)
        if tag is None:
            document = await self.db.find_one({"$or":[{"name":{"$eq":name}}, {"aliases":{"$in":[name]}}]})
            if document is None:
                raise TagNotFound(f"Tag with name '{name}' couldn't be found in the database.")
            tag = TagEntry(data=document)


        if isinstance(tag, TagEntry):
            data = tag.raw
            if update_uses:
                data['uses'] = tag.uses + 1
                await self.db.update_one({'_id':tag.id}, {'$set':{'uses':tag.uses}})
            tag = TagEntry(data=data)
            for alias in tag.aliases:
                self._cache[alias] = tag
            self._cache[tag.name] = tag

        return tag

    async def create_tag(self, user:discord.User, name:str, content) -> bool:
        created = datetime.utcnow()
        document = {
            'owner':user.id,
            'name':name,
            'content':content,
            'uses':0,
            'created':created,
            'aliases':[]
        }

        tag = await self.db.insert_one(document=document)
        document['_id'] = tag.inserted_id

        self._cache[name] = TagEntry(data=document)

        return tag.acknowledged

    @botchannel()
    @commands.group(invoke_without_command=True)
    async def tag(self, ctx:commands.Context, *, name:str):
        """ Shows a tag. """
        tag = await self.get_tag(name=name, update_uses=True)
        await ctx.send(tag.content, reference=self.replied_reference(ctx.message))

    @botchannel()
    @tag.command()
    async def info(self, ctx:commands.Context, *,name:str):
        """ Shows info on a tag."""
        tag = await self.get_tag(name=name, update_uses=True)

        embed = discord.Embed(
            title = tag.name,
            colour = self.bot.invisible_colour,
            timestamp = tag.created,
            description = f"*Tag ID: {tag.id}*"
        )
        embed.add_field(
            name="Owner",
            value=f"<@{tag.owner_id}>",
        )
        embed.add_field(
            name="Uses",
            value=tag.uses
        )
        embed.add_field(
            name="Aliases",
            value=len(tag.aliases)
        )
        embed.set_footer(text="Tag Created At")

        await ctx.send(embed=embed)

    @botchannel()
    @tag.command()
    async def aliases(self, ctx:commands.Context, *, name:str):
        """ Shows aliases of a tag. """
        tag = await self.get_tag(name=name)
        embed = discord.Embed(
            title = f"{len(tag.aliases)} Aliases found.",
            colour = self.bot.invisible_colour,
            timestamp = datetime.utcnow()
        )
        description = ""
        for i, alias in enumerate(tag.aliases, start=1):
            description += f"{i}. {alias}"

        embed.description = description

        await ctx.send(embed=embed)

    @botchannel()
    @tag.command(hidden=True, name='repr')
    async def show_repr(self, ctx:commands.Context, *, name:str):
        """ Shows a repr of the tag. If you don't know what this is, then this is not for you. """
        tag = await self.get_tag(name=name)
        await ctx.send(repr(tag))

    @botchannel()
    @tag.command(hidden=True, name='dict', aliases=['rawdict'])
    async def tag_dict(self, ctx:commands.Context, *, name:str):
        """ Shows the raw data of the tag. """
        tag = await self.get_tag(name=name)

        await jskpagination(ctx, str(tag.raw))

    @botchannel()
    @tag.command()
    async def raw(self, ctx:commands.Context, *, name:str):
        """ Shows raw information about a tag. Escapes markdown and mentions. """
        tag = await self.get_tag(name=name, update_uses=True)

        await ctx.send(discord.utils.escape_markdown(tag.content))

    @botchannel()
    @tag.command()
    async def create(self, ctx:commands.Context, name:str, *, content:commands.clean_content):
        """ Creates a tag. """
        cmds = ctx.command.parent.commands
        for c in cmds:
            if (name == c.name) or (name in c.aliases):
                return await ctx.send(f'{name} is reserved keyword and cannot be used to create a tag.')

        try:
            tag = await self.get_tag(name=name)
            if tag:
                return await ctx.send(f'{tag} is already a registered tag.')
        except TagNotFound:
            tag = await self.create_tag(ctx.author, name, content)
            if tag:
                await ctx.send(f'Successfully created the tag: {name}')
            else:
                await ctx.send('Unable to create a tag at the moment.')

    @admin()
    @tag.command()
    async def cache(self, ctx:commands.Context):
        """ Shows the internal Cache. """
        await jskpagination(ctx, str(self._cache))


    @botchannel()
    @tag.command()
    async def delete(self, ctx:commands.Context, *,name:str):
        """ Deletes a tag. """
        tag = await self.get_tag(name=name)
        if (tag.owner_id == ctx.author.id) or (await self.bot.is_owner(ctx.author)):
            await self.db.delete_one({'name':name})
            del self._cache[name]
            return await ctx.send('Succesfully deleted the tag!')

        elif tag.owner_id in ADMINS:
            return await ctx.send('Cannot delete a tag made by another admin.')

        elif ctx.author.guild_permissions.administrator:
            await self.db.delete_one({'name':name})
            del self._cache[name]
            return await ctx.send('Succesfully deleted the tag!')

        else:
            return await ctx.reply('You do not own this tag.')

    @botchannel()
    @tag.command()
    async def edit(self, ctx:commands.Context, name:str, *, content:commands.clean_content):
        """ Edits a tag. """
        tag = await self.get_tag(name=name)

        if tag.owner_id == ctx.author.id:
            await self.db.update_one({'name':name},{"$set":{'content':content}})
            await ctx.reply('Successfully edited the tag.')
        else:
            await ctx.send('You cannot edit someone elses tag.')

        data = tag.raw
        data['content'] = content

        tag = TagEntry(data=data)

        for alias in tag.aliases:
            self._cache[alias] = tag
            self._cache[tag.name] = tag

    @botchannel()
    @tag.command(usage="<new name> <old name>")
    async def alias(self, ctx:commands.Context, newname:str, *, oldname:str):
        """ Adds an alias to a tag. """

        old = await self.get_tag(name=oldname, update_uses=False)
        try:
            new = await self.get_tag(name=newname, update_uses=False)
        except TagNotFound:
            new = None

        if (old is not None) and (new is None):
            data = old.raw
            aliases = old.aliases
            if newname in aliases:
                return await ctx.send('Alias is already there.')
            aliases.append(newname)
            if old.owner_id == ctx.author.id:
                await self.db.update_one({'name':oldname}, {'$set':{'aliases':aliases}})
                data['aliases'] = aliases
                tag = TagEntry(data=data)
                for alias in tag.aliases:
                    self._cache[alias] = tag
                    self._cache[tag.name] = tag
                return await ctx.send(f"Tag alias '{newname}' that points to '{oldname}' successfully created.")
            else:
                return await ctx.send("You do not own the tag.")
        else:
            return await ctx.send(f"Cannot find the tag: **{oldname}**")

    @botchannel()
    @tag.command()
    async def search(self, ctx:commands.Context, *, name:str):
        """ Searches for a tag. """
        async for doc in self.db.find():
            doc:dict
            tag = TagEntry(data=doc)
            self._cache[tag.name] = tag
            for alias in tag.aliases:
                self._cache[alias] = TagEntry(data=doc)

        matches = get_close_matches(name, list(self._cache.keys()), n=10, cutoff=0.5)
        if len(matches) > 0:
            tags = [(await self.get_tag(n)) for n in matches]
            try:
                p = TagPages(entries=tags, per_page=20, colour=self.bot.invisible_colour)
            except menus.MenuError as e:
                await ctx.send(e)
            else:
                await p.start(ctx)
        else:
            await ctx.send("No tags found.")


    @botchannel()
    @tag.command()
    async def claim(self, ctx:commands.Context, *, name:str):
        """ Claims a tag. """
        tag = await self.get_tag(name, update_uses=False)
        if tag.owner_id in [m.id for m in ctx.guild.members]:
            return await ctx.send("The tag owner is still in the guild.")
        else:
            await self.db.update_one({'name':name}, {'$set':{'owner':ctx.author.id}})
            data = {
                '_id':tag.id,
                'owner':ctx.author.id,
                'name':name,
                'content':tag.content,
                'uses':tag.uses,
                'created':tag.created,
                'aliases':tag.aliases
            }
            self._cache[name] = TagEntry(data=data)
            return await ctx.send("Succesfully claimed the tag.")

    @botchannel()
    @tag.command()
    async def transfer(self, ctx:commands.Context, name:str, user:discord.Member):
        """ Transfers a tag. """
        tag = await self.get_tag(name, update_uses=False)
        if tag.owner_id == ctx.author.id:
            await self.db.update_one({'name':name}, {'$set':{'owner':user.id}})
            data = {
            '_id':tag.id,
            'owner':user.id,
            'name':name,
            'content':tag.content,
            'uses':tag.uses,
            'created':tag.created,
            'aliases':tag.aliases
            }
            self._cache[name] = TagEntry(data=data)
            return await ctx.send(content=f"Successfully transferred the tag to {user.name}")
        else:
            return await ctx.send("You do not own this tag.")

    @botchannel()
    @tag.command(name="list")
    async def _list(self, ctx:commands.Context, user:Optional[discord.User]):
        "Lists a tag by a user."
        user = user or ctx.author
        tags = self.db.find({'owner':user.id})
        _all = []
        async for tag in tags:
            _all.append(TagEntry(data=tag))

        if _all:
            try:
                p = TagPages(entries=_all, per_page=20, colour=self.bot.invisible_colour)
            except menus.MenuError as e:
                await ctx.send(e)
            else:
                await p.start(ctx)
        else:
            await ctx.send("No tags found.")

    @botchannel()
    @tag.command(name='all')
    async def _all(self, ctx:commands.Context, user:Optional[discord.User]):
        """ Shows all tags by a user or in the guild. """
        if user:
            await ctx.invoke(self._list, user=user)
        else:
            tags = [TagEntry(data=tag) async for tag in self.db.find({})]
            if tags:
                try:
                    p = TagPages(entries=tags, per_page=20, colour=self.bot.invisible_colour)
                except menus.MenuError as e:
                    await ctx.send(e)
                else:
                    await p.start(ctx)
            else:
                await ctx.send("No tags found.")

    @botchannel()
    @commands.command()
    async def tags(self, ctx:commands.Context, *, user:Optional[discord.User]):
        """Lists tags by a user"""
        user = user or ctx.author
        await ctx.invoke(self._list, user=user)


def setup(bot):
    bot.add_cog(Tags(bot))
