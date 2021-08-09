"""
Error Handler Module - Handles CommandErrors
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

import traceback
import aiohttp
import discord

from typing import Optional
from discord.ext import commands
from jishaku.paginators import PaginatorEmbedInterface
from utils import Context, Bot, utcnow, is_bot_channel, format_date, Embed

def signature(ctx: Context):
    if not ctx.valid:
        return 'N/A'
    cmd = ctx.command
    return f'{ctx.clean_prefix}{cmd.qualified_name} {cmd.signature}'

class Handler(commands.Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: Bot):
        self.bot = bot

    @staticmethod
    async def log_error(ctx: Context, trace: str, error):
        async def get_id() -> int:
            ids = []
            async for doc in ctx.bot.errors.find({}):
                ids.append(doc['id'])
            if ids:
                return ids.pop()+1
            else:
                return 1

        document = {
            'id':await get_id(),
            'message':ctx.message.content,
            'author':f'{ctx.author} ({ctx.author.id})',
            'resolved':False,
            'traceback':trace,
            'type':error.__class__.__name__
        }

        insert = await ctx.bot.errors.insert_one(document)
        return (insert, document)

    async def mystbin(self, data: str, session: aiohttp.ClientSession):
        data = bytes(data, 'utf-8')
        async with session.post('https://mystb.in/documents', data=data) as r:
            res = await r.json()
            key = res['key']
            url = f'https://mystb.in/{key}.python'
        
        return url

    async def post_error(self, ctx: Context, session: aiohttp.ClientSession, data: str, id: int):
        
        url = await self.mystbin(data, ctx.session)

        embed = discord.Embed(
            title='An Unexpected Error Occurred',
            colour=discord.Colour.red(),
            timestamp=utcnow()
        )
        embed.set_footer(text=f'Error Number: {id}')
        embed.add_field(
            name='Command Used',
            value=f'`{ctx.message.content}`',
            inline=False
        )
        embed.add_field(
            name='Author',
            value=f'{ctx.author} (ID: {ctx.author.id})',
            inline=False
        )

        view = discord.ui.View()
        button = discord.ui.Button(style=discord.ButtonStyle.link, label='View Error', url=url, emoji='⚠')
        view.add_item(button)
        return await ctx.send(embed=embed, view=view)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: Context, error: commands.CommandError):
        if hasattr(ctx.command, 'on_error'):
            return

        ignored = (commands.CommandNotFound,)

        error = getattr(error, 'original', error)

        cog: commands.Cog = ctx.cog
        if cog:
            if cog._get_overridden_method(cog.cog_command_error) is not None:
                return        

        if isinstance(error, ignored):
            return

        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.reply(f'You forgot to provide the `{error.param.name}` argument while using the command. Refer `{signature(ctx)}`?')

        elif isinstance(error, (commands.UserNotFound, commands.MemberNotFound)):
            return await ctx.reply(f'Could not find the user `{error.argument}`. Try again?')

        elif isinstance(error, commands.RoleNotFound):
            return await ctx.reply(f'Could not find the role `{error.argument}`. Try again?')
        
        elif isinstance(error, commands.CheckFailure):
            return await ctx.reply(f'You probably do not have enough permissions to use `{ctx.command.qualified_name}` command.')

        elif isinstance(error, AttributeError) and ctx.guild is None:
            return await ctx.reply(f'Cannot use `{ctx.command.qualified_name}` command in DMs')

        elif isinstance(error, commands.BadArgument):
            return await ctx.send(error)

        elif isinstance(error, discord.Forbidden):
            return await ctx.send(f'That action is forbidden. Maybe you are missing permissions?\nDiscord-side message: {str(error)}')

        else:
            error_type = type(error)
            trace = error.__traceback__
            lines = traceback.format_exception(error_type, error, trace)
            text = ''.join(lines)

            _, document = await self.log_error(ctx, text, error)
            print(await self.post_error(ctx, ctx.session, text, document['id']))
            raise error

    @commands.group(invoke_without_command=True)
    @is_bot_channel()
    async def error(self, ctx: Context, id: int):
        """Shows an error's info"""

        document = await ctx.bot.errors.find_one({'id':id})
        if document is None:
            return await ctx.send('Invalid Id provided. Maybe the error was already resolved and deleted?')

        embed = discord.Embed(
            title=f'Error Number {document["id"]}',
            colour=ctx.color,
            timestamp=document['_id'].generation_time
        )

        solved = '<:yesTick:818793909982461962>' if document['resolved'] else '<:noTick:811230315648647188>'
        if document['resolved'] is None:
            solved = '<:maybeTick:853693562113622077>'

        embed.set_footer(text='Occurred at')
        embed.add_field(name='Message', value=document['message'], inline=False)
        embed.add_field(name='Author', value=document['author'], inline=False)
        embed.add_field(name='Resolved', value=solved, inline=False)
        embed.add_field(name='Type', value=document.get('type', 'None'), inline=False)

        url = await self.mystbin(document['traceback'], ctx.session)

        view = discord.ui.View()
        button = discord.ui.Button(style=discord.ButtonStyle.link, label='View Error', url=url, emoji='⚠')
        view.add_item(button)
        await ctx.send(embed=embed, view=view)

    async def update_resolve(self, ctx: Context, id: int, value: bool):
        document = await ctx.bot.errors.find_one({'id':id})
        if document is None:
            return await ctx.send('Invalid Id provided. Maybe the error was already resolved and deleted?')

        await ctx.bot.errors.update_one({'id':id}, {'$set':{'resolved':value}})
        await ctx.tick(True)

    @error.command(aliases=['resolved'])
    @commands.is_owner()
    async def resolve(self, ctx: Context, id: commands.Greedy[int]):
        """Marks an error as resolved"""
        for I in id:
            await self.update_resolve(ctx, I, True)

    @error.command(aliases=['unresolved'])
    @commands.is_owner()
    async def unresolve(self, ctx: Context, id: commands.Greedy[int]):
        """Marks an error as unresolved"""
        for I in id:
            await self.update_resolve(ctx, I, False)

    @error.command()
    @commands.is_owner()
    async def wontfix(self, ctx: Context, id: commands.Greedy[int]):
        """Marks an error as unresolved"""
        for I in id:
            await self.update_resolve(ctx, I, None)

    @error.command()
    @commands.is_owner()
    async def delete(self, ctx: Context, id: commands.Greedy[int]):
        """Deletes an error log."""
        for I in id:
            option = False
            deleted = await ctx.bot.errors.delete_one({'id':I})
            if deleted.deleted_count >= 1:
                option = True

            await ctx.tick(option)

    @is_bot_channel()
    @commands.command()
    async def errors(self, ctx: Context, Type: Optional[str]):
        """Shows all errors"""

        search = []

        async for err in ctx.bot.errors.find({}):
            solved = '<:yesTick:818793909982461962>' if err['resolved'] else '<:noTick:811230315648647188>'
            if err['resolved'] is None:
                solved = '<:maybeTick:853693562113622077>'
            query = f'{err["id"]} - {err["type"]} ({format_date(err["_id"].generation_time)}) {solved}'
            if Type is None:
                search.append(query)
            else:
                if err['type'].casefold() == Type.casefold():
                    search.append(query)

        if search:
            embed = Embed(title='All Errors Reported', colour=ctx.color)
            paginator = commands.Paginator(prefix=None, suffix=None, max_size=500)
            for e in search:
                paginator.add_line(e)
       
            interface = PaginatorEmbedInterface(self.bot, paginator, owner=ctx.author, embed=embed)
            await interface.send_to(ctx)
        else:
            await ctx.send('No errors found.')

def setup(bot: Bot):
    bot.add_cog(Handler(bot))