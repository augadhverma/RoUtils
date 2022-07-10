"""
Handles the moderation cog of the bot.
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

import discord
import datetime
import re

from discord.ext import commands
from discord import app_commands
from utils import EmbedPages, Embed, Context, has_permissions, has_setting_role

from typing import Any, Callable, Literal, Union, Optional, TypedDict
from collections import Counter

from utils import Bot, Infraction, InfractionType, ReasonError

SHOW_DELETED = Literal['Yes', 'No']
SHOW_DELETED_DESCRIPTION = 'Whether to show infractions deleted from user\'s profile.'
REASON = 'The reason for the infraction.'
HIERARCY_ERROR_MESSAGE = 'You cannot do this action on this user due to role hierarchy.'
SEARCH = 'The number of messages to search.'

def get_until(**kwargs) -> float:
    """Gets the future timestamp.

    kwargs: days, seconds, microseconds, milliseconds, minutes, hours, weeks

    Returns
    -------
    float
        The future timestamp.
    """
    return discord.utils.utcnow().timestamp() + datetime.timedelta(**kwargs).total_seconds()

def can_execute_action(interaction: discord.Interaction, moderator: discord.Member, offender: discord.Member) -> bool:
    return (
        moderator.id == interaction.client.owner_id or 
        moderator == interaction.guild.owner or 
        moderator.top_role > offender.top_role if isinstance(offender, discord.Member) else True
    )

class ActionReason(TypedDict):
    original_reason: str
    reason: str

class ReasonTransformer(app_commands.Transformer):
    @classmethod
    async def transform(cls, interaction: discord.Interaction, value: str) -> ActionReason:
        reason = f"{value} (Reason by {interaction.user} ID: {interaction.user.id})"
        if len(reason) > 512:
            reason_max = 512 - len(reason) + len(value)
            raise ReasonError(f"Reason is too long ({len(value)}/{len(reason_max)})")
        return ActionReason(original_reason=value, reason=reason)

class InfractionPageEntry:
    def __init__(self, infraction: Infraction) -> None:
        title = f"{infraction.case} | {infraction.created.strftime('%Y-%m-%d')}"
        description = infraction.embed_description('log')
        self.field = (title, description)

class InfractionPages(EmbedPages):
    def __init__(self, entries: list[Infraction], *, interaction: discord.Interaction, bot: Bot, per_page=5, **kwargs) -> None:
        converted = [InfractionPageEntry(entry).field for entry in entries]
        super().__init__(converted, per_page=per_page, interaction=interaction, bot=bot, **kwargs)

class Moderation(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    async def on_infraction(
        self,
        action: Union[discord.Interaction, Context],
        offender: Union[discord.User, discord.Member],
        infraction: Infraction
    ):
        if isinstance(action, discord.Interaction):
            ctx = await self.bot.get_context(action, cls=Context)
        else:
            ctx = action
        try:
            await ctx.send(embed=infraction.embed('channel'))
        except discord.InteractionResponded:
            await ctx.send(embed=infraction.embed('channel'))

        log = await self.bot.post_log(ctx.guild, 'bot', embed=infraction.embed('log'))
        
        try:
            await offender.send(f"Sent from {ctx.guild.name}", embed=infraction.embed('offender'))
        except discord.HTTPException:
            pass

        if not isinstance(offender, discord.Member):
            return

        # Checks only infracions that are not deleted from the user's profile.
        count = 0
        async for inf in self.bot.infractions.find({'guild_id':ctx.guild.id, 'offender':offender.id}):
            inf = Infraction(inf)
            if not inf.deleted:
                count += 1

        #count >= 5 → Kick
        #count >=3 → Automute/Autotimeout

        if count >= 5:
            reason = f"Autokick from {ctx.guild.name} (Reached {count} infractions)."
            new = await self.bot.insert_infraction(
                offender.id,
                self.bot.user.id,
                reason,
                InfractionType.kick,
                get_until(days=30),
                ctx.guild.id
            )

            try:
                await self.on_infraction(action, offender, new)
                await offender.kick(reason=reason)
                
            except Exception as e:
                if log:
                    await log.reply(f"Could not kick the user\nError that occured: `{e}`")
                pass
            finally:
                return

        elif count >= 3:
            settings = await self.bot.get_guild_settings(ctx.guild.id)
            if settings.timeout_instead_of_mute:
                reason = f"Auto-timeout in {ctx.guild.name} (Reached {count} infractions)."
                
                try:
                    await offender.timeout(datetime.timedelta(hours=3), reason=reason)
                except Exception as e:
                    if log:
                        await log.reply(f"Could not kick the user\nError that occured: `{e}`")
                    pass

                new = await self.bot.insert_infraction(
                    offender.id,
                    self.bot.user.id,
                    reason,
                    InfractionType.autotimeout,
                    get_until(hours=3),
                    ctx.guild.id
                )
                await self.on_infraction(action, offender, new)
                return
                
            else:
                if settings.mute_role:
                    role = action.guild.get_role(settings.mute_role)
                    if role is None:
                        pass
                    else:
                        try:
                            await offender.add_roles(role, reason=reason)
                        except Exception as e:
                            if log:
                                await log.reply(f"Could not kick the user\nError that occured: `{e}`")
                            pass
                    
                        new = await self.bot.insert_infraction(
                                offender.id,
                                self.bot.user.id,
                                reason,
                                InfractionType.autotimeout,
                                get_until(hours=3),
                                ctx.guild.id
                            )

                        await self.on_infraction(action, offender, new)
                        return
                else:
                    pass

    @has_permissions(moderate_members=True)
    @app_commands.command(name="info", description="Shows information about an infraction.")
    @app_commands.describe(id="The id of the infraction.", show_deleted=SHOW_DELETED_DESCRIPTION)
    async def info(self, interaction: discord.Interaction, id: int, show_deleted: Optional[SHOW_DELETED]) -> None:
        infraction = await self.bot.get_infraction(id, interaction.guild_id)
        if infraction is None:
            return await interaction.response.send_message(f"The infraction #{id} does not exist.")
        else:
            if infraction.deleted and show_deleted == 'No':
                return await interaction.response.send_message(f"The infraction #{id} does not exist.")
            return await interaction.response.send_message(embed=infraction.embed('log'))

    @has_permissions(moderate_members=True)
    @app_commands.command(name="warn", description="Warns a user")
    @app_commands.describe(user="The user to warn.", reason=REASON)
    async def warn(self, interaction: discord.Interaction, user: discord.Member, reason: str) -> None:
        if can_execute_action(interaction, interaction.user, user) is False:
            return await interaction.response.send_message(HIERARCY_ERROR_MESSAGE, ephemeral=True)

        infraction = await self.bot.insert_infraction(
            user.id,
            interaction.user.id,
            reason,
            InfractionType.warn,
            get_until(days=15),
            interaction.guild_id
        )

        await self.on_infraction(interaction, user, infraction)

    @has_permissions(kick_members=True)
    @app_commands.command(name="kick", description="Kicks a user from the server.")
    @app_commands.describe(user="The user to kick.", reason=REASON)
    async def kick(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: app_commands.Transform[ActionReason, ReasonTransformer]
    ) -> None:
        if can_execute_action(interaction, interaction.user, user) is False:
            return await interaction.response.send_message(HIERARCY_ERROR_MESSAGE, ephemeral=True)
        
        infraction = await self.bot.insert_infraction(
            user.id,
            interaction.user.id,
            reason["original_reason"],
            InfractionType.kick,
            get_until(days=30),
            interaction.guild_id
        )

        await self.on_infraction(interaction, user, infraction)

        try:
            await user.kick(reason=reason["reason"])
        except discord.HTTPException:
            await interaction.followup.send("An unknown error occured.")

    @has_permissions(ban_members=True)
    @app_commands.command(name="ban", description="Bans a user from the server.")
    @app_commands.describe(user="The user to ban.", reason=REASON)
    async def ban(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        delete_messages: Optional[Literal['Don\'t Delete Any', 'Previous 24 Hours', 'Previous 7 Days']],
        reason: app_commands.Transform[ActionReason, ReasonTransformer]
    ) -> None:
        if can_execute_action(interaction, interaction.user, user) is False:
            return await interaction.response.send_message(HIERARCY_ERROR_MESSAGE, ephemeral=True)
        
        to_delete = 1
        
        if delete_messages == "Don't Delete Any":
            to_delete = 0
        elif delete_messages == "Previous 24 Hours":
            to_delete = 1
        elif delete_messages == "Previous 7 Days":
            to_delete = 7

        infraction = await self.bot.insert_infraction(
            user.id,
            interaction.user.id,
            reason["original_reason"],
            InfractionType.ban,
            get_until(days=10000),
            interaction.guild_id
        )

        await self.on_infraction(interaction, user, infraction)

        try:
            await interaction.guild.ban(user, reason=reason["reason"], delete_message_days=to_delete)
        except discord.HTTPException:
            await interaction.followup.send("An unknown error occured.")

    @has_permissions(ban_members=True)
    @app_commands.command(name="unban", description="Unbans a user from the server.")
    @app_commands.describe(user="The user to unban.", reason="The reason for unban.")
    async def unban(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        reason: app_commands.Transform[ActionReason, ReasonTransformer]
    ) -> None:
        
        try:
            await interaction.guild.unban(user, reason=reason["reason"])
        except discord.NotFound:
            return await interaction.response.send_message(f"{user} is not banned.")
        infraction = await self.bot.insert_infraction(
            user.id,
            interaction.user.id,
            reason["original_reason"],
            InfractionType.unban,
            get_until(days=10000),
            interaction.guild_id
        )

        await self.on_infraction(interaction, user, infraction)

    @has_permissions(moderate_members=True)
    @app_commands.command(name="removewarn", description="Removes an infraction.")
    @app_commands.describe(id="The id of the removal.")
    async def removewarn(self, interaction: discord.Interaction, id: int) -> None:
        infraction = await self.bot.get_infraction(id, interaction.guild_id)
        if infraction is None:
            return await interaction.response.send_message(f"Infraction with id #{id} does not exist.")
        
        await self.bot.infractions.update_one({'_id':infraction._id}, {'$set':{'deleted':True}})
        
        await interaction.response.send_message(f"Successfully removed the infraction #{id}", embed=infraction.embed("log"))

    @has_permissions(moderate_members=True)
    @app_commands.command(name="reason", description="Changes the reason for an infraction.")
    @app_commands.describe(id="The id of the infraction.", reason="The new reason.")
    async def new_reason(
        self,
        interaction: discord.Interaction,
        id: int,
        reason: app_commands.Transform[ActionReason, ReasonTransformer]
    ) -> None:
        infraction = await self.bot.get_infraction(id, interaction.guild_id)
        if infraction is None:
            return await interaction.response.send_message(f"Infraction with id #{id} does not exist.")
        await self.bot.infractions.update_one({"_id":infraction._id}, {"$set":{"reason":reason["reason"]}})
        embed = Embed(
            bot=self.bot,
            title="Success",
            colour=discord.Colour.green(),
            description=f"New reason:\n{reason['original_reason']}"
        )
        await interaction.response.send_message(embed=embed)

    @has_permissions(manage_messages=True)
    @app_commands.command(name="slowmode", description="Changes the slowmode of channels.")
    @app_commands.describe(
        channel="The channel who's slowmode needs to be updated or viewed.",
        delay="The slowmode delay to set."
    )
    async def slowmode(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel],
        delay: Optional[str]
    ) -> None:
        channel = channel or interaction.channel
        current = channel.slowmode_delay

        if delay is None:
            return await interaction.response.send_message(
                f"Slowmode for {channel.mention} is `{current}` seconds."
            )
        if delay.casefold() == "off":
            delay = 0
        elif delay and delay[0] in ("+", "-"):
            delay = current + int(delay)
            if delay < 0:
                delay = 0
            elif delay > 21600:
                delay = 21600
        elif delay:
            delay = int(delay)

        try:
            await channel.edit(slowmode_delay=delay)
            await interaction.response.send_message(f"Slowmode set to `{delay}` seconds in {channel.mention}.")
        except Exception as e:
            await interaction.followup.send(f"An unknown error occured\n{e}")

    purge = app_commands.Group(name="purge", description="The purge command group")

    # https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/mod.py#L1320-L1362
    async def do_removal(
        self,
        interaction: discord.Interaction,
        limit: int,
        predicate: Callable[[discord.Message], Any],
        *,
        before: Optional[int] = None,
        after: Optional[int] = None,
    ):

        ctx = await self.bot.get_context(interaction, cls=Context)

        if limit > 2000:
            return await interaction.response.send_message(f'Too many messages to search given ({limit}/2000)')

        if before is None:
            passed_before = ctx.message
        else:
            passed_before = discord.Object(id=before)

        if after is not None:
            passed_after = discord.Object(id=after)
        else:
            passed_after = None

        try:
            deleted = await ctx.channel.purge(limit=limit, before=passed_before, after=passed_after, check=predicate)
        except discord.Forbidden as e:
            return await interaction.response.send_message('I do not have permissions to delete messages.')
        except discord.HTTPException as e:
            return await interaction.response.send_message(f'Error: {e} (try a smaller search?)')

        spammers = Counter(m.author.display_name for m in deleted)
        deleted = len(deleted)
        messages = [f'{deleted} message{" was" if deleted == 1 else "s were"} removed.']
        if deleted:
            messages.append('')
            spammers = sorted(spammers.items(), key=lambda t: t[1], reverse=True)
            messages.extend(f'**{name}**: {count}' for name, count in spammers)

        to_send = '\n'.join(messages)

        if len(to_send) > 2000:
            await interaction.response.send_message(f'Successfully removed {deleted} messages.', ephemeral=True)
        else:
            await interaction.response.send_message(to_send, ephemeral=True)

    @has_permissions(manage_messages=True)
    @purge.command(name="all", description="Removes all messages.")
    @app_commands.describe(search=SEARCH)
    async def purge_all(self, interaction: discord.Interaction, search: int = 100) -> None:
        await self.do_removal(interaction, search, lambda e: True)

    @has_permissions(manage_messages=True)
    @purge.command(name="embeds", description="Removes messages that have embeds in them.")
    @app_commands.describe(search=SEARCH)
    async def embeds(self, interaction: discord.Interaction, search: int = 100) -> None:
        await self.do_removal(interaction, search, lambda e: len(e.embeds))

    @has_permissions(manage_messages=True)
    @purge.command(name="files", description="Removes messages that have attachments in them.")
    @app_commands.describe(search=SEARCH)
    async def files(self, interaction: discord.Interaction, search: int = 100) -> None:
        await self.do_removal(interaction, search, lambda e: len(e.attachments))
    
    @has_permissions(manage_messages=True)
    @purge.command(name="images", description="Removes messages that have embeds or attachments.")
    @app_commands.describe(search=SEARCH)
    async def images(self, interaction: discord.Interaction, search: int = 100) -> None:
        await self.do_removal(interaction, search, lambda e: len(e.attachments) or len(e.embeds))

    @has_permissions(manage_messages=True)
    @purge.command(name="user", description="Removes all messages by a member.")
    @app_commands.describe(search=SEARCH, member="The member whose messages have to be purged.")
    async def user(self, interaction: discord.Interaction, member: discord.Member, search: int = 100) -> None:
        await self.do_removal(interaction, search, lambda e: e.author == member)

    @has_permissions(moderate_members=True)
    @app_commands.command(name="warns", description="Shows warns received by/given to a user.")
    @app_commands.describe(option="The option to show.", user="The user whose warns are being shown.", show_deleted=SHOW_DELETED_DESCRIPTION)
    async def warns(
        self,
        interaction: discord.Interaction,
        option: Literal['Given by', 'Received by'],
        user: discord.User,
        show_deleted: Optional[SHOW_DELETED]
    ) -> None:
        if option == 'Given by':
            value='moderator'
        elif option == 'Received by':
            value='offender'

        _all = []
        async for document in self.bot.infractions.find({'guild_id':interaction.guild_id, value:user.id}):
            infraction = Infraction(document)
            if infraction.deleted and show_deleted == 'Yes':
                _all.append(infraction)
            else:
                _all.append(infraction)

        if _all:
            embed = Embed(
                bot=self.bot,
                title=f"{len(_all)} infractions found."
            )
            pages = InfractionPages(_all, interaction=interaction, bot=self.bot, embed=embed)
            await pages.start()
        else:
            await interaction.response.send_message("No infractions found.")

    @commands.Cog.listener('on_message')
    async def detection(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return
        if not message.channel.permissions_for(message.guild.me):
            return

        if message.author.guild_permissions.manage_messages:
            return

        ctx = await self.bot.get_context(message, cls=Context)

        if (await has_setting_role(ctx, 'bypass')):
            return

        settings = await self.bot.get_guild_settings(message.guild.id)

        if settings.bad_word_detection:
            for word in settings.bad_words:
                regex = re.compile('\s*'.join(word), re.IGNORECASE)
                L = regex.findall(message.content)
                if L:
                    try:
                        await message.delete()
                    except discord.NotFound:
                        return
                    infraction = await self.bot.insert_infraction(
                        message.author.id,
                        self.bot.user.id,
                        f"Using a blacklisted word (||{L[0]}||)",
                        InfractionType.autowarn,
                        get_until(days=1),
                        message.guild.id
                    )

                    await self.on_infraction(ctx, message.author, infraction)

        if settings.domain_detection:
            url_regex = re.compile('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', re.IGNORECASE)
            for link in settings.domains_whitelisted:
                if link in message.content.casefold():
                    return
            else:
                L = url_regex.findall(message.content)
                if L:
                    try:
                        await message.delete()
                    except discord.NotFound:
                        return
                
                infraction = await self.bot.insert_infraction(
                    message.author.id,
                    self.bot.user.id,
                    f"Using a blacklisted link (||{L[0]}||)",
                    InfractionType.autowarn,
                    get_until(days=1),
                    message.guild.id
                )
                
                await self.on_infraction(ctx, message.author, infraction)

            invite_regex = re.compile('(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/[a-zA-Z0-9]+/?', re.IGNORECASE)

            L = invite_regex.findall(message.content)
            if L:
                try:
                    invite = await commands.InviteConverter().convert(ctx, L[0])
                    if invite.guild == ctx.guild:
                        return
                except commands.BadArgument:
                    return
                else:
                    try:
                        await message.delete()
                    except discord.HTTPException:
                        pass

                    infraction = await self.bot.insert_infraction(
                        message.author.id,
                        self.bot.user.id,
                        f"Using a blacklisted invite (||{L[0]}||)",
                        InfractionType.autowarn,
                        get_until(days=1),
                        message.guild.id
                    )

                    await self.on_infraction(ctx, message.author, infraction)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Moderation(bot))