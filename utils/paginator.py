import asyncio
import discord
from discord.ext import menus
from discord.ext.commands import Paginator
from jishaku.paginators import PaginatorInterface, WrappedPaginator

class EmbedPageSource(menus.ListPageSource):
    def __init__(self, embeds):
        super().__init__(embeds, per_page=1)

    async def format_page(self, menu, page):
        return await super().format_page(menu, page)


async def jskpagination(ctx, content, wrap_on=('\n',' ',','), force_wrap=True, prefix='```yaml', suffix='```', max_size=1985, **kwargs):
        paginator = WrappedPaginator(wrap_on=wrap_on, force_wrap=force_wrap, max_size=max_size, prefix=prefix, suffix=suffix, **kwargs)
        paginator.add_line(content)
        interference = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
        await interference.send_to(ctx)