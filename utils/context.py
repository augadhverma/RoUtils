"""
Bot's command Context.
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

import aiohttp
import discord

from typing import Optional
from discord.ext import commands

class Context(commands.Context):
    message: discord.Message

    def __init__(self, **attrs):
        from utils.bot import Bot
        self.bot: Bot = attrs.get('bot', None)
        super().__init__(**attrs)

    def __repr__(self) -> str:
        return '<Context>'

    @property
    def session(self) -> aiohttp.ClientSession:
        return self.bot.session

    @property
    def version(self) -> str:
        return self.bot.__version__

    @property
    def colour(self) -> int:
        return self.bot.colour

    color = colour

    @property
    def footer(self) -> str:
        return self.bot.footer

    async def tick(self, opt:Optional[bool]=True) -> None:
        lookup = {
            True:'<:yesTick:818793909982461962>',
            False:'<:noTick:811230315648647188>',
            None:'<:maybeTick:853693562113622077>'
        }
        
        emoji = lookup.get(opt, '<:noTick:811230315648647188>')
        try:
            return await self.message.add_reaction(emoji)
        except discord.HTTPException:
            pass

    async def loading(self, remove: bool = False) -> None:
        emoji = '<a:loading:801422257221271592>'
        try:
            if remove:
                await self.message.clear_reaction(emoji)
                await self.tick(True)
            else:
                return await self.message.add_reaction(emoji)
        except discord.HTTPException:
            pass

    async def reply(self, content=None, *, mention=False, **kwargs) -> discord.Message:
        msg: discord.Message = self.message

        default_mentions = discord.AllowedMentions.none()

        allowed_mentions = kwargs.pop('allowed_mentions', default_mentions)
        mention_author = kwargs.pop('mention_author', mention)

        return await msg.reply(
            content=content, 
            allowed_mentions=allowed_mentions,
            mention_author=mention_author,
            **kwargs
        )


    @discord.utils.cached_property
    def replied_reference(self):
        ref = self.message.reference
        if ref and isinstance(ref.resolved, discord.Message):
            return ref.resolved.to_reference()
        return None

    @discord.utils.cached_property
    def channel(self):
        return self.message.channel

    @discord.utils.cached_property
    def guild(self):
        return self.message.guild

    async def post_log(self, **kwargs):
        settings = await self.bot.utils.find_one({'type':'settings'})
        guild: discord.Guild = self.message.guild

        channel = guild.get_channel(settings['log'])
        if channel is None:
            try:
                channel = await guild.fetch_channel(settings['log'])
            except (discord.HTTPException, discord.InvalidData):
                return await self.send('Fetching the log channel failed, cannot post log for the current action', delete_after=10.0)

        return await channel.send(**kwargs)