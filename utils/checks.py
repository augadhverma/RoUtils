# Based on Rapptz RoboDanny's checks
# https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/utils/checks.py

import discord

from typing import Literal, Union
from discord import app_commands
from discord.ext import commands

from .context import Context
from .bot import Bot
from .errors import CannotUseBotCommand



ROLE = Literal['admin', 'bypass']

ROWIFI_HELP_FORUM = 1006727091083038800

async def get_context(action: Union[discord.Interaction, Context]) -> Context:
    if isinstance(action, discord.Interaction):
        return await action.client.get_context(action, cls=Context)
    return action

async def check_perms(
    action: Union[Context, discord.Interaction],
    perms: dict[str, bool],
    *,
    check=all
) -> bool:
    if isinstance(action, discord.Interaction):
        ctx: Context = await action.client.get_context(action, cls=Context)
        error = app_commands.NoPrivateMessage()
    else:
        ctx = action
        error = commands.NoPrivateMessage()

    is_owner = await ctx.bot.is_owner(ctx.author)
    if is_owner:
        return True

    if ctx.guild is None:
        raise error

    resolved = ctx.channel.permissions_for(ctx.author)
    return check(getattr(resolved, name, None) == value for name, value in perms.items())

async def has_setting_role(action: Union[discord.Interaction, Context], role: ROLE) -> bool:
    ctx = await get_context(action)
    pre = await check_perms(action, {'administrator':True})
    if pre:
        return True
    
    bot: Bot = ctx.bot
    settings = await bot.get_guild_settings(ctx.guild.id)

    user_roles: list[int] = [r.id for r in ctx.author.roles]
    if settings.extra_roles[role] in user_roles:
        return True
    elif settings.extra_roles['admin'] in user_roles:
        return True
    else:
        return False

def has_permissions(slash=True, *, check=all, **perms: bool):
    async def pred(action: Union[discord.Interaction, Context]):
        pre_check = (
            await check_perms(action, perms, check=check) or
            await has_setting_role(action, 'admin')
        )

        if pre_check:
            return True
        
        permissions = action.permissions
        missing = [perm for perm, value in perms.items() if getattr(permissions, perm) != value]
        if missing:
            if isinstance(action, discord.Interaction):
                raise app_commands.MissingPermissions(missing)
            else:
                raise commands.MissingPermissions(missing)
        else:
            return True
    if slash:
        return app_commands.check(pred)
    else:
        return commands.check(pred)

def is_admin():
    async def pred(interaction: discord.Interaction):
        return await has_setting_role(interaction, 'admin')
    return app_commands.check(pred)

def can_bypass():
    async def pred(interaction: discord.Interaction):
        return await has_setting_role(interaction, 'bypass')
    return app_commands.check(pred)

def is_mod(senior=False):
    async def pred(interaction: discord.Interaction):
        ctx = await get_context(interaction)
        pre = await has_setting_role(interaction, 'admin')

        if pre:
            return True

        bot: Bot = ctx.bot
        user_roles: list[int] = [r.id for r in ctx.author.roles]
        
        settings = await bot.get_guild_settings(interaction.guild_id)

        if senior and (settings.mod_roles['senior mod'] in user_roles):
            return True
        elif settings.mod_roles['mod'] in user_roles and (senior is not True):
            return True
        else:
            return False
    return app_commands.check(pred)

def is_bot_channel():
    async def pred(interaction: discord.Interaction):
        pre = (
            await has_setting_role(interaction, 'bypass') or
            await check_perms(interaction, {'manage_messages':True})
        )
        if pre:
            return True
        
        bot: Bot = interaction.client
        settings = await bot.get_guild_settings(interaction.guild_id)

        if interaction.channel_id in settings.command_disabled_channels:
            raise CannotUseBotCommand(interaction.channel)
        else:
            return True
    return app_commands.check(pred)

def can_close_threads():
    async def predicate(action: Union[discord.Interaction, Context]):
        ctx = await get_context(action)
        if not isinstance(ctx.channel, discord.Thread):
            return False
            
        settings = await ctx.bot.get_guild_settings(ctx.guild.id)

        user_roles = [r.id for r in ctx.author.roles]

        return ctx.channel.parent_id == ROWIFI_HELP_FORUM and (
            (any(x in settings.mod_roles.values() for x in user_roles)) or ctx.channel.owner_id == ctx.author.id
        )

    return commands.check(predicate)