import asyncio
import datetime
import discord

from discord.ext import commands, menus
import humanize

from jishaku.paginators import PaginatorInterface, WrappedPaginator

from typing import List, Union
from utils.utils import InfractionEntry, InfractionType, TagEntry

# RoboPages is from RoboDanny
# https://github.com/Rapptz/RoboDanny/blob/0dfa21599da76e84c2f8e7fde0c132ec93c840a8/cogs/utils/paginator.py

class RoboPages(menus.MenuPages):
    def __init__(self, source, **kwargs):
        super().__init__(source=source,check_embeds=True, **kwargs)
        self.input_lock = asyncio.Lock()

    async def finalize(self, timed_out):
        try:
            if timed_out:
                await self.message.clear_reactions()
            else:
                await self.message.delete()
        except discord.HTTPException:
            pass

    @menus.button('\N{INFORMATION SOURCE}\ufe0f', position=menus.Last(3))
    async def show_help(self, payload):
        """shows this message"""
        embed = discord.Embed(title='Paginator help', description='Hello! Welcome to the help page.')
        messages = []
        for (emoji, button) in self.buttons.items():
            messages.append(f'{emoji}: {button.action.__doc__}')

        embed.add_field(name='What are these reactions for?', value='\n'.join(messages), inline=False)
        embed.set_footer(text=f'We were on page {self.current_page + 1} before this message.')
        await self.message.edit(content=None, embed=embed)

        async def go_back_to_current_page():
            await asyncio.sleep(30.0)
            await self.show_page(self.current_page)

        self.bot.loop.create_task(go_back_to_current_page())


    @menus.button('\N{INPUT SYMBOL FOR NUMBERS}', position=menus.Last(1.5), lock=False)
    async def numbered_page(self, payload):
        """lets you type a page number to go to"""
        if self.input_lock.locked():
            return

        async with self.input_lock:
            channel = self.message.channel
            author_id = payload.user_id
            to_delete = []
            to_delete.append(await channel.send('What page do you want to go to?'))

            def message_check(m):
                return m.author.id == author_id and \
                       channel == m.channel and \
                       m.content.isdigit()

            try:
                msg = await self.bot.wait_for('message', check=message_check, timeout=30.0)
            except asyncio.TimeoutError:
                to_delete.append(await channel.send('Took too long.'))
                await asyncio.sleep(5)
            else:
                page = int(msg.content)
                to_delete.append(msg)
                await self.show_checked_page(page - 1)

            try:
                await channel.delete_messages(to_delete)
            except Exception:
                pass

async def jskpagination(ctx, content, wrap_on=('\n',' ',','), force_wrap=True, prefix='```yaml', suffix='```', max_size=1985, **kwargs):
        paginator = WrappedPaginator(wrap_on=wrap_on, force_wrap=force_wrap, max_size=max_size, prefix=prefix, suffix=suffix, **kwargs)
        paginator.add_line(content)
        interference = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
        await interference.send_to(ctx)

class SimplePageSource(menus.ListPageSource):
    def __init__(self, entries, *, per_page=12):
        super().__init__(entries, per_page=per_page)
        self.initial_page = True

    async def format_page(self, menu, entries):
        pages = []
        for index, entry in enumerate(entries, start=menu.current_page * self.per_page):
            pages.append(f'{index + 1}. {entry}')

        maximum = self.get_max_pages()
        if maximum > 1:
            footer = f'Page {menu.current_page + 1}/{maximum} ({len(self.entries)} entries)'
            menu.embed.set_footer(text=footer)

        if self.initial_page and self.is_paginating():
            pages.append('')
            pages.append('Confused? React with \N{INFORMATION SOURCE} for more info.')
            self.initial_page = False

        menu.embed.description = '\n'.join(pages)
        return menu.embed

class FieldPageSource(menus.ListPageSource):
    """Requires (field_name, field_value)"""
    def __init__(self, entries, *, per_page=6, colour=discord.Colour.teal()):
        super().__init__(entries, per_page=per_page)
        self.embed = discord.Embed(colour=colour)

    async def format_page(self, menu, entries):
        self.embed.clear_fields()
        self.embed.description = discord.Embed.Empty

        for key, value in entries:
            self.embed.add_field(name=key, value=value, inline=False)
        
        maximum = self.get_max_pages()
        if maximum > 1:
            text = f"Page {menu.current_page+1}/{maximum} ({len(self.entries)} entries)"

            self.embed.set_footer(text=text)
        return self.embed

class SimplePages(RoboPages):
    def __init__(self, entries, *, per_page=12, colour=discord.Colour.blurple()):
        super().__init__(SimplePageSource(entries, per_page=per_page))
        self.embed = discord.Embed(colour=colour)

class TagPageEntry:
    __slots__ = ('name', 'uses')

    def __init__(self, entry:Union[TagEntry, dict]):
        if isinstance(entry, TagEntry):
            self.name = entry.name
            self.uses = entry.uses
        else:
            self.name = entry['name']
            self.uses = entry['uses']

    def __str__(self):
        return f"{self.name} *(uses: {self.uses})*"

class TagPages(SimplePages):
    def __init__(self, entries, *, per_page=12, colour=discord.Colour.blurple()):
        converted = [TagPageEntry(entry) for entry in entries]
        super().__init__(converted, per_page=per_page, colour=colour)

class InfractionPageEntry:
    def __init__(self, entry:dict, show_mod=True):
        self.id = entry['id']
        self.type = InfractionType(entry['type']).name
        self.mod = f"**Moderator:** <@{entry['moderator']}>"
        self.offender = f"**Offender:** <@{entry['offender']}>"
        self.reason = f"**Reason:** {entry['reason']}"
        
        if entry['until'] and entry['time']:
            delta = datetime.timedelta(seconds=entry['until']-entry['time']) 
            self.until = humanize.precisedelta(delta)
            self.valid = f"**Valid Until:** {self.until}"
        else:
            self.valid = ""

        self.key = f"#{self.id} | {self.type}"
        if show_mod:
            mod = f"{self.mod}\n"
        else:
            mod = ""

        self.value = f"{mod}"\
                     f"{self.offender}\n"\
                     f"{self.reason}\n"\
                     f"{self.valid}"

class InfractionPages(RoboPages):
    def __init__(self, entries, *, per_page=6, colour=discord.Colour.teal(), show_mod=True):
        converted = [(InfractionPageEntry(entry, show_mod).key, InfractionPageEntry(entry, show_mod).value) for entry in entries]
        super().__init__(FieldPageSource(converted, per_page=per_page, colour=colour))