import discord
import re
from cogs.info import TICKETLOGS, TICKETCATEGORY

import utils

from discord.ext import commands

from utils import Bot, Context
from jishaku.paginators import PaginatorEmbedInterface

class Tickets(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @utils.is_intern()
    @commands.command(invoke_without_command=True)
    async def ticket(self, ctx: Context, *, member: discord.Member = None):
        """Shows tickets handled by a staff member."""

        await ctx.loading()
        if member is None and ctx.author.guild_permissions.administrator:
            member = None
        else:
            member = member or ctx.author
        now = utils.utcnow()
        reference = None
        handled = []
        unclaimed = []
        if now.month == 1:
            after = now.replace(month=12)
        else:
            after = now.replace(month=now.month-1)

        channel: discord.TextChannel = ctx.guild.get_channel(TICKETLOGS)
        if channel is None:
            return await ctx.reply('Cannot fetch logs right now. Try again later.')
            
        url_regex = re.compile('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', re.IGNORECASE)

        async for message in channel.history(limit=None, after=after):
            if message.embeds and message.author.id == 508391840525975553:
                embed = message.embeds[0]
                t_id = embed.fields[0].value
                staff = embed.fields[-1].value
                if staff == 'Not claimed':
                    unclaimed.append(staff)
                archive = url_regex.findall(embed.fields[-3].value)[0]

                if reference is None:
                    reference = message

                if member is None:
                    handled.append(f'[Ticket {t_id} - {staff}]({archive})')
                else:
                    try:
                        staff = await commands.UserConverter().convert(ctx, staff)
                    except:
                        pass
                    else:
                        if staff.id == member.id:
                            handled.append(f'[Ticket {t_id}]({archive})')

        embed = discord.Embed(
            title = f'Tickets handled by {f"{member}" if member else "Staff Team"}',
            colour = discord.Colour.blue()
        )

        embed.add_field(
            name='Duration',
            value=f'**From:** {utils.format_date(after)}\n**Until:** {utils.format_date(now)}',
            inline=False
        )

        embed.set_author(name='Reference', url=reference.jump_url)

        if len(handled) == 0:
            await ctx.loading(True)
            return await ctx.send(f'No tickets to show for {member}.')

        paginator = commands.Paginator(prefix='', suffix='', max_size=2000)
        for i,t in enumerate(handled, 1):
            paginator.add_line(f'{i}. {t.replace(")", "", 1)}')

        interface = PaginatorEmbedInterface(self.bot, paginator, owner=ctx.author, embed=embed)

        await interface.send_to(ctx)
        await ctx.loading(True)

        if unclaimed:
            if member is None and ctx.author.guild_permissions.administrator:
                await ctx.reply(f'Unclaimed: {len(unclaimed)}\nClaimed: {len(handled)-len(unclaimed)}\nTotal: {len(handled)}')


def setup(bot: Bot):
    bot.add_cog(Tickets(bot))