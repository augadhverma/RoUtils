"""
The Tags Module - For custom tags.
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
from jishaku.paginators import PaginatorEmbedInterface
import utils
from utils.checks import INTERN, check_perms

from typing import Optional
from discord.ext import commands
from difflib import get_close_matches
from bson.objectid import ObjectId

class Tags(commands.Cog):
    def __init__(self, bot: utils.Bot) -> None:
        self.bot = bot

    async def cog_command_error(self, ctx: utils.Context, error: commands.CommandError):
        error = getattr(error, 'original', error)
        if isinstance(error, RuntimeError):
            await ctx.send(error)
        elif isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
            if ctx.command.qualified_name == 'tag':
                await ctx.send_help(ctx.command)
            else:
                await ctx.send(str(error))
        else:
            raise error

        

    async def get_tag(self, name: str, *, update_uses=False) -> utils.TagEntry:
        document = await self.bot.tags.find_one({"$or":[{"name":{"$eq":name}}, {"aliases":{"$in":[name]}}]})
        if document is None:
            search = []
            async for t in self.bot.tags.find({}):
                search.append(t['name'])
                for a in t.get('aliases', []):
                    search.append(a)

            matches = get_close_matches(name, search)
            if matches:
                raise RuntimeError('Tag not found. Did you mean...\n'+"\n".join(m for m in matches))
            else:
                raise RuntimeError('Tag not found.')
        
        tag = utils.TagEntry(document)

        if update_uses:
            tag.uses += 1
            await self.bot.tags.update_one(
                {'_id':tag.id},
                {'$set':{'uses':tag.uses}}
            )

        return tag

    def extra_info(self, tag: utils.TagEntry) -> str:
        has_content = False
        has_image = True if tag.image else False
        has_button = True if tag.url else False

        if tag.content and tag.content != '\uFEFF':
            has_content = True

        to_return = (f'Extra Information about the tag:\n'
                     f'→ Content: {has_content}\n'
                     f'→ Has an Embed: {tag.embed}\n'
                     f'→ Has an Embed Image: {has_image}\n'
                     f'→ Has an URL Button: {has_button}\n')

        if has_button:
            to_return += f'The Button "{tag.url[0]}" points to <{tag.url[1]}>'

        return to_return


    @utils.is_bot_channel()
    @commands.group(invoke_without_command=True)
    async def tag(self, ctx: utils.Context, *, name: str):
        """Allows you to tag text for later retrieval.

        If a subcommand is not called, then this will search the tag database
        for the tag requested.
        """

        tag = await self.get_tag(name, update_uses=True)
        items = tag.to_send()
        view = items[1]
        if isinstance(items[0], discord.Embed):
            await ctx.send(embed=items[0], view=view, reference=ctx.replied_reference)
        elif isinstance(items[0], str):
            await ctx.send(items[0], view=view, reference=ctx.replied_reference)

    @utils.is_bot_channel()
    @tag.command()
    async def info(self, ctx: utils.Context, name: str, *, flags: utils.TagOptions):
        """Retrieves info about a tag.

        The info includes things like the owner and how many times it was used.

        Flags:
        `extra:` true/t/y/yes - Shows extra info on the ticket.
        """

        tag = await self.get_tag(name, update_uses=True)

        m = await ctx.reply(embed=tag.to_embed())
        if flags.extra.casefold() in ('true', 't', 'yes', 'y'):
            await m.reply(self.extra_info(tag))

    @utils.is_bot_channel()
    @tag.command()
    async def delete(self, ctx: utils.Context, *, name: str):
        """Removes a tag that you own.

        The tag owner can always delete their own tags. If someone requests
        deletion and has Administrator permissions then they can also
        delete it.

        Deleting a tag will delete all of its aliases as well.
        """

        tag = await self.get_tag(name)

        if (tag.owner_id == ctx.author.id or
            ctx.authr.guild_permissions.administrator == True):
            
            r = await self.bot.tags.delete_one({'_id':tag._id})
            await ctx.reply(f'Successfully deleted tag "{tag.name}" and its components.')

        else:
            raise RuntimeError('You do not own this tag and hence cannot delete it.')

    @utils.is_bot_channel()
    @tag.command()
    async def create(self, ctx: utils.Context, name: str, *, flags: utils.TagOptions):
        """Creates a new tag owned by you.

        You can integrate more options to your tag using the flags:

        content: Content of tag. [Optional]
        url: Name,URL (example -> Website , https://rowifi.link) [Optional] (Adds a button that points to the URL with the Name as the label)
        embed: true/false [Optional] (Shows the tag output in an embed)
        image: URL [Optional] (Setting this will make the tag into an embed) (Adds an image to the the embed)

        Note that server moderators can delete your tag.
        """

        for cmd in ctx.bot.walk_commands():
            if (cmd.name == name) or (name in cmd.aliases):
                return await ctx.send(f'**{name}** is a reserved keyword and cannot be used to make tags.') 

        try:
            await self.get_tag(name)
        except RuntimeError:
            pass
        else:
            return await ctx.send(f'{name} is already an existing tag.')

        document = {
            'name': name,
            'content':flags.content or '\uFEFF',
            'uses': 0,
            'created':utils.utcnow(),
            'aliases':[],
            'owner':ctx.author.id
        }

        if flags.embed:
            if flags.embed.casefold() == 'true':
                document['embed'] = True
            elif flags.embed.casefold() == 'false':
                document['embed'] = False
            else:
                raise RuntimeError('Invalid options provided. Valid options are: `true` and `false`')

        if flags.image:
            if flags.image.startswith('http'):
                document['image'] = flags.image
                document['embed'] = True
            else:
                raise RuntimeError('Invalid URL was provided, please provide an URL that starts with http(s).')

        if flags.url:
            try:
                name, url = flags.url.replace(' ,', ',').replace(', ', ',').split(',', 1)
            except ValueError:
                raise RuntimeError('Got multiple commas (`,`), expected only one.')
            else:
                document['url'] = [name, url]

        r = await self.bot.tags.insert_one(document)
        
        await ctx.reply(f'Successfully created the tag\nYou can reference it using the id: `{r.inserted_id}`')
            
    @utils.is_bot_channel()
    @tag.command()
    async def edit(self, ctx: commands.Context, name: str, *, flags: utils.TagOptions):
        """Modifies an existing tag that you own.

        Takes same flags as tag create

        `content: Content of the tag.` [Optional]
        `url: Name,URL` (example -> Website , https://rowifi.link) [Optional]
        (Adds a button that points to the URL with the Name as the label)
        `embed: true/false` [Optional] (Shows the tag output in an embed)
        `image: URL` [Optional] (Setting this will make the tag into an embed)
        (Adds an image to the the embed)

        Couple of things to note, having an image by default will
        enable the embed. You can pass in `none` to the flag fields
        to get rid of them (like, image: none will remove the embed 
        image)

        To edit the aliases of the tags, use the tag alias command.

        This command completely replaces the original text. If
        you want to get the old text back, consider using the
        tag raw command.
        """
        tag = await self.get_tag(name)


        if tag.owner_id != ctx.author.id:
            raise RuntimeError('You do not own this tag and hence cannot modify it.')

        if flags.content:
            if flags.content.casefold() == 'none':
                tag.content = '\uFEFF'
            else:
                tag.content = flags.content

        if flags.url:
            try:
                name, url = flags.url.replace(' ,', ',').replace(', ', ',').split(',', 1)
            except ValueError:
                if flags.url.casefold() == 'none':
                    tag.url = None
                else:
                    raise RuntimeError('Got multiple commas (`,`), expected only one.')
            else:
                tag.url = [name, url]

        if flags.embed:
            if flags.embed.casefold() == 'true' or tag.image:
                tag.embed = True
            else:
                tag.embed = False

        if flags.image:
            if flags.image.casefold() == 'none':
                tag.image = None
            else:
                tag.image = flags.image
                tag.embed = True

        
        r = await self.bot.tags.collection.replace_one({'_id':tag._id}, tag.to_dict())
        await ctx.reply('Successfully updated the tag!')

    @utils.is_bot_channel()
    @tag.command()
    async def raw(self, ctx: utils.Context, name: str, *, flags: utils.TagOptions):
        """Gets the raw content of the tag.

        This is with markdown escaped. Useful for editing.
        
        Flags:
        `extra:` true/t/yes/y - Shows extra info on the tag.
        """

        tag = await self.get_tag(name, update_uses=True)
        
        if tag.content and tag.content != '\uFEFF':
            content = discord.utils.escape_markdown(tag.content)
        else:
            content = tag.content
        
        m = await ctx.reply(content)

        if flags.extra.casefold() in ('true', 't', 'yes', 'y'):
            await m.reply(self.extra_info(tag))
        

    @utils.is_bot_channel()
    @tag.command()
    async def search(self, ctx: utils.Context, *, query: str):
        """Searches for a tag.

        The query must be at least 2 characters.
        """

        if len(query) < 2:
            return await ctx.send('The query must be at least 2 characters.')

        search = []

        async for t in self.bot.tags.find({}):
            search.append(t['name'])
            for a in t.get('aliases', []):
                search.append(a)

        matches = get_close_matches(query, search, n=int(len(search)//1.5), cutoff=0.45)

        if matches:
            embed = discord.Embed(title='Close matches found', colour=ctx.colour)
            paginator = commands.Paginator(prefix='', suffix='', max_size=350)
            for i,t in enumerate(matches, 1):
                paginator.add_line(f'{i}. {t}')

            interface = PaginatorEmbedInterface(self.bot, paginator, owner=ctx.author, embed=embed)

            await interface.send_to(ctx)
        else:
            await ctx.reply('Could not find the tag.')

    @utils.is_bot_channel()
    @tag.command(name='list')
    async def _list(self, ctx: utils.Context, *, user: Optional[discord.User]):
        """Lists all the tags that belong to you or someone else."""

        user = user or ctx.author

        search: list[str] = []
        async for t in self.bot.tags.find({'owner':user.id}):
            search.append(f"{t['name']} *(uses: {t['uses']})*")
                

        if search:
            embed = discord.Embed(title=f'All tags owned by {user}', colour=ctx.colour)
            paginator = commands.Paginator(prefix='', suffix='', max_size=350)
            for i,t in enumerate(search, 1):
                paginator.add_line(f'{i}. {t}')

            interface = PaginatorEmbedInterface(self.bot, paginator, owner=ctx.author, embed=embed)

            await interface.send_to(ctx)
        else:
            await ctx.reply(f'**{user}** does not own any tags.')

    @utils.is_bot_channel()
    @tag.command(name='all')
    async def _all(self, ctx: utils.Context):
        """Shows all server tags."""
        search = []

        async for t in self.bot.tags.find({}):
            uses = t['uses']
            search.append(f"{t['name']} *(uses: {uses})*")

        if search:
            embed = discord.Embed(title='All Server Specific Tags', colour=ctx.colour)
            paginator = commands.Paginator(prefix='', suffix='', max_size=350)
            for i,t in enumerate(search, 1):
                paginator.add_line(f'{i}. {t}')

            interface = PaginatorEmbedInterface(self.bot, paginator, owner=ctx.author, embed=embed)

            await interface.send_to(ctx)
        else:
            await ctx.reply(f'No tags were found for the server.')

    @utils.is_bot_channel()
    @tag.command()
    async def transfer(self, ctx: utils.Context, name: str, *, member: discord.Member):
        """Transfers a tag to another member.

        You must own the tag before doing this.
        """

        tag = await self.get_tag(name)

        if tag.owner_id == ctx.author.id:
            await self.bot.tags.update_one({'_id':tag._id}, {'$set':{'owner': member.id}})
            await ctx.reply(f'Successfully transferred {tag.name} to {member}')         
        else:
            return await ctx.reply('You do not own this tag and hence cannot transfer it.')

    @utils.is_bot_channel()
    @tag.command()
    async def claim(self, ctx: utils.Context, *, name: str):
        """Claims an unclaimed tag.

        An unclaimed tag is a tag that effectively
        has no owner because they have left the server.
        """

        tag = await self.get_tag(name)

        try:
            member = await commands.MemberConverter().convert(ctx, str(tag.owner_id))
        except commands.BadArgument:
            await self.bot.tags.update_one({'_id':tag._id}, {'$set':{'owner': ctx.author.id}})
            await ctx.reply(f'Successfully claimed the tag "{name}".')
        else:
            await ctx.reply('The tag owner is still in this server.')

    @utils.is_bot_channel()
    @tag.command(aliases=['aliases'])
    async def alias(self, ctx: utils.Context, name: str, *, flags: utils.TagAlias):
        """Add or remove aliases from a tag.
        
        Usage: (Separate the aliases by commas `,`)
        Adding an alias - add: hello, hi
        Removing an alias - remove: hello, hi
        """

        tag = await self.get_tag(name)

        if tag.owner_id != ctx.author.id:
            return await ctx.send('You do not own this tag.')

        if not flags._add and not flags.remove:
            embed = discord.Embed(colour=ctx.colour, title=f'Aliases for tag: {tag.name}')
            embed.description = '\n'.join(f'{i}. {a}' for i,a in enumerate(tag.aliases, 1)) or discord.Embed.Empty
            return await ctx.reply(embed=embed)
        
        cmds: set[commands.Command] = ctx.command.parent.commands

        if flags._add:
            to_add = flags._add.replace(' ,', ',').replace(', ', ',').split(',')
        else:
            to_add = []
        if flags.remove:
            to_remove = flags.remove.replace(' ,', ',').replace(', ', ',').split(',')
        else:
            to_remove = []

        for a in to_add:
            try:
                await self.get_tag(a)
            except RuntimeError:
                pass
            else:
                return await ctx.send(f'{a} is an existing tag. Please try again.')
            for c in cmds:
                if (a.casefold() == c.name.casefold() or
                    a.casefold() in [b.casefold() for b in c.aliases]):
                    return await ctx.send(f'{a} is a reserved key word and cannot be used to create an alias.')
                else:
                    tag.aliases.append(a)

        for a in to_remove:
            try:
                tag.aliases.remove(a)
            except IndexError:
                pass

        aliases = list(set(tag.aliases))

        await self.bot.tags.update_one({'_id':tag._id}, {'$set':{'aliases':aliases}})
        
        await ctx.tick(True)

    @utils.is_admin()
    @tag.command()
    async def prune(self, ctx: utils.Context, uses: int = 0):
        """Prunes tags which have not been used atleast once or have been
        used less than or equal to the uses provided.
        
        Once deleted, there is no recovering of the tags.
        """


        r = await self.bot.tags.delete_many({'uses':{'$lte':uses}})
        await ctx.reply(f'Successfully deleted {r.deleted_count} tags.')

    @utils.is_bot_channel()
    @tag.command(name='id', usage='<id>')
    async def _id(self, ctx: utils.Context, *, name: str):
        """Get a tag by using its id."""

        tag = await self.bot.tags.find_one({'_id':ObjectId(name)})
        if tag is None:
            return await ctx.reply('Invalid id provided, I could not find the tag using that id.')

        tag = utils.TagEntry(tag)
        items = tag.to_send()
        view = items[1]
        if isinstance(items[0], discord.Embed):
            await ctx.send(embed=items[0], view=view, reference=ctx.replied_reference)
        elif isinstance(items[0], str):
            await ctx.send(items[0], view=view, reference=ctx.replied_reference)
        await ctx.invoke(self.info, name=tag.name)

        await self.bot.tags.update_one({'_id':tag._id}, {'$set':{'uses':tag.uses+1}})

    @utils.is_bot_channel()
    @commands.command()
    async def tags(self, ctx: utils.Context, *, user: Optional[discord.User]):
        """An alias for tag list command."""

        user = user or ctx.author

        await ctx.invoke(self._list, user=user)

    @commands.Cog.listener("on_message")
    async def message_tags(self, message: discord.Message):
        pre_checks = (
            message.author.bot
            or message.guild is None
        )

        if pre_checks:
            return

        ctx = await self.bot.get_context(message, cls=utils.Context)
        if ctx.valid:
            return
        if ctx.prefix and message.content.startswith(ctx.prefix):
            _, name = message.content.split(ctx.prefix, maxsplit=1)
        else:
            return

        perms = await check_perms(ctx, {'manage_messages':True})
        is_intern = INTERN in [r.id for r in message.author.roles]

        if not (perms or is_intern):
            settings: dict = await ctx.bot.utils.find_one({'type':'settings'})

            if ctx.channel.id in settings.get('disabledChannels', []):
                return

        try:
            tag = await self.get_tag(name, update_uses=True)
        except RuntimeError:
            pass
        else:
            items = tag.to_send()
            view = items[1]
            if isinstance(items[0], discord.Embed):
                await ctx.send(embed=items[0], view=view, reference=ctx.replied_reference)
            elif isinstance(items[0], str):
                await ctx.send(items[0], view=view, reference=ctx.replied_reference)

def setup(bot: utils.Bot):
    bot.add_cog(Tags(bot))