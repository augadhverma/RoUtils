"""
Gives raw output of various Roblox APIs.

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


from discord.ext import commands, menus
from bot import RoUtils
from utils.paginator import RawPageSource
from utils import cache

urlCache = cache.TimedCache(seconds=3600)
groupCache = cache.TimedCache(seconds=3600)
rolesCache = cache.TimedCache(seconds=1800)


group = "https://groups.roblox.com/v1/groups"

class RawAPI(commands.Cog):
    def __init__(self, bot:RoUtils):
        self.bot = bot

    async def get_json_content(self, url:str) -> dict:
        """Gives raw json of the url given.

        Parameters
        ----------
        url : str
            The url to get the json object of.

        Returns
        -------
        dict
            The result json.
        """
        r = await self.bot.session.get(url)
        return await r.json()


    @commands.group(invoke_without_command=True)
    async def raw(self, ctx:commands.Context, url:str):
        raw = urlCache.get(url, None)
        if raw is None:
            raw = await self.get_json_content(url=url)
            raw = str(raw)
            urlCache[url] = raw
        max_size = 500
        if len(raw) < 800:
            max_size = 1000
        menu = menus.MenuPages(RawPageSource(raw, prefix="```yaml", max_size=max_size))
        await menu.start(ctx)

    @raw.command()
    async def roles(self, ctx:commands.Context, group_id:int):
        raw = rolesCache.get(group_id, None)
        if raw is None:
            raw = await self.get_json_content(url=f"{group}/{group_id}/roles")
            raw = str(raw)
            rolesCache[group_id] = raw
        max_size = 500
        if len(raw) < 800:
            max_size = 1000
        menu = menus.MenuPages(RawPageSource(raw, prefix="```yaml", max_size=max_size))
        await menu.start(ctx)
        
    @raw.command()
    async def group(self, ctx:commands.Context, group_id:int):
        raw = groupCache.get(group_id, None)
        if raw is None:
            raw = await self.get_json_content(url=f"{group}/{group_id}")
            raw = str(raw)
            groupCache[group_id] = raw
        max_size = 500
        if len(raw) < 800:
            max_size = 1000
        menu = menus.MenuPages(RawPageSource(raw, prefix="```yaml", max_size=max_size))
        await menu.start(ctx)

    

              

def setup(bot:RoUtils):
    bot.add_cog(RawAPI(bot))