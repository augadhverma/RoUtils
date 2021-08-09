from discord.ext import commands

from .context import Context

INTERN = 783068153856131072

async def check_perms(ctx: Context, perms: dict, *, check=all) -> bool:
    is_owner = await ctx.bot.is_owner(ctx.author)
    if is_owner:
        return True

    if ctx.guild is None:
        return False

    resolved = ctx.author.guild_permissions
    return check(getattr(resolved, name, None) == value for name, value in perms.items())

def is_admin():
    async def pred(ctx: Context):
        return await check_perms(ctx, {'administrator':True})
    return commands.check(pred)

def is_staff(*, senior=False):
    if senior:
        check=all
    else:
        check=any
    async def pred(ctx: Context):
        return await check_perms(ctx, {'manage_messages':True, 'manage_nicknames':True}, check=check)
    return commands.check(pred)


def is_intern():
    async def pred(ctx: Context):
        perms = await check_perms(ctx, {'manage_messages':True})
        if perms:
            return True
        roles = [r.id for r in ctx.author.roles]
        if INTERN in roles:
            return True
        
        return False
    return commands.check(pred)

def is_bot_channel():
    async def pred(ctx: Context):
        perms = await check_perms(ctx, {'manage_messages':True})
        if perms:
            return True
        if ctx.guild is None:
            return False
        roles = [r.id for r in ctx.author.roles]
        if INTERN in roles:
            return True

        settings: dict = await ctx.bot.utils.find_one({'type':'settings'})

        if ctx.channel.id in settings.get('disabledChannels', []):
            return False
        return True
    return commands.check(pred)