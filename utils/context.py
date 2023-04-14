"""
The bot's context
Copyright (C) 2021-present ItsArtemiz (Augadh Verma)

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

from typing import Any, Optional
import aiohttp
import discord

from discord.ext import commands

class Context(commands.Context):
    message: discord.Message
    def __init__(self, **attrs):
        self.bot = attrs.get('bot', None)
        super().__init__(**attrs)

    def __repr__(self) -> str:
        return '<Context>'

    @property
    def session(self) -> aiohttp.ClientSession:
        return self.bot.sesion

    @property
    def colour(self) -> int:
        return self.bot.colour

    @property
    def footer(self) -> str:
        return self.bot.footer
    
    @discord.utils.cached_property
    def replied_reference(self) -> Optional[discord.MessageReference]:
        ref = self.message.reference
        if ref and isinstance(ref.resolved, discord.Message):
            return ref.resolved.to_reference()
        return None