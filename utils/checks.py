"""
This Discord Bot has been made to keep the server of RoWifi safe and a better place for everyone

Copyright © 2020 ItsArtemiz (Augadh Verma). All rights reserved.

This Software is distributed with the GNU General Public License (version 3).
You are free to use this software, redistribute it and/or modify it under the
terms of GNU General Public License version 3 or later.

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of this Software.

This Software is provided AS IS but WITHOUT ANY WARRANTY, without the implied
warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

For more information on the License, check the LICENSE attached with this Software.
If the License is not attached, see https://www.gnu.org/licenses/
"""

from discord.ext import commands

staff = 652203841978236940
senior_staff = 693896132882989086


async def check_permissions(ctx:commands.Context, perms, *, check=all):
    is_owner = await ctx.bot.is_owner(ctx.author)
    if is_owner:
        return True

    resolved = ctx.channel.permissions_for(ctx.author)
    return check(getattr(resolved, name, None) == value for name, value in perms.items())

def has_permissions(*, check=all, **perms):
    async def pred(ctx):
        return await check_permissions(ctx, perms, check=check)
    return commands.check(pred)

async def check_guild_permissions(ctx, perms, *, check=all):
    is_owner = await ctx.bot.is_owner(ctx.author)
    if is_owner:
        return True

    if ctx.guild is None:
        return False

    resolved = ctx.author.guild_permissions
    return check(getattr(resolved, name, None) == value for name, value in perms.items())

def has_guild_permissions(*, check=all, **perms):
    async def pred(ctx):
        return await check_guild_permissions(ctx, perms, check=check)
    return commands.check(pred)

def is_admin():
    async def pred(ctx:commands.Context):
        if await ctx.bot.is_owner(ctx.author):
            return True
        else:
            return await check_guild_permissions(ctx, {"administrator":True})
    return commands.check(pred)

def is_staff():
    async def pred(ctx:commands.Context):
        if is_admin():
            return True
        elif staff in [r.id for r in ctx.author.roles]:
            return True
        else:
            return False
    return commands.check(pred)

def is_senior_staff():
    async def pred(ctx:commands.Context):
        if is_admin():
            return True
        elif senior_staff in [r.id for r in ctx.author.roles]:
            return True
        else:
            return False
    return commands.check(pred)