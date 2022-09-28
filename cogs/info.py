"""
Things related to information of users.
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

import json
import re
import discord
import datetime

from discord import app_commands
from discord.ext import commands

from utils import (
    Bot,
    is_bot_channel,
    User,
    RoWifiUser,
    request,
    Embed,
    Cache,
    Member,
    TextPages,
    format_dt,
    check_perms,
    has_setting_role,
    Context,
    SimplePages
)

from typing import Optional, Union

ROWIFIAPI = 'https://api.rowifi.link/v1/users/{0}?guild_id={1}'
USER = 'https://users.roblox.com/v1/users/{0}'
GROUP = 'https://groups.roblox.com/{0}/{1}'

class TicketPageEntry:
    def __init__(self, entry: str):
        self.entry = entry
    
    def __str__(self) -> str:
        return self.entry.replace("))", ")", 1)

class TicketPages(SimplePages):
    def __init__(self, entries: list[str], *, interaction: discord.Interaction, bot: Bot, per_page: int = 12, **kwargs) -> None:
        converted = [TicketPageEntry(entry) for entry in entries]
        
        super().__init__(converted, per_page=per_page, interaction=interaction, bot=bot, **kwargs)

class Information(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.__rowifi_user_cache = Cache(seconds=180) #{'discord_id-guild_id':user, }
        self.__user_cache = Cache() #{roblox_id:user, }
        self.__member_cache = Cache(seconds=180) #{roblox_id-group_id, member}

    async def get_user(self, roblox_id: int, /) -> User:
        if self.__user_cache.get(roblox_id):
            return self.__user_cache[roblox_id]

        data = await request(self.bot.session, 'GET', USER.format(roblox_id))
        user = User(data)

        self.__user_cache[roblox_id] = user
        return user

    async def get_rowifi_user(self, discord_id: int, guild_id: int, /) -> RoWifiUser:
        if self.__rowifi_user_cache.get(f'{discord_id}-{guild_id}'):
            return self.__rowifi_user_cache[f'{discord_id}-{guild_id}']

        data = await request(self.bot.session, 'GET', ROWIFIAPI.format(discord_id, guild_id))

        user = RoWifiUser(discord_id, guild_id, data['success'])

        if data['success']:
            roblox_user = await self.get_user(data['roblox_id'])
            user.roblox_user = roblox_user

        self.__rowifi_user_cache[f'{discord_id}-{guild_id}'] = user
        return user

    @is_bot_channel()
    @app_commands.command(name="userinfo", description="Shows information about the user.")
    @app_commands.describe(user="The user whose information to show.")
    async def userinfo(self, interaction: discord.Interaction, user: Optional[Union[discord.User, discord.Member]]) -> None:
        user = user or interaction.user
        embed = Embed(
            bot=self.bot,
            title="User Information",
            description=""
        )
        embed.set_author(name=str(user), icon_url=user.display_avatar.url)

        rowifi_user = await self.get_rowifi_user(user.id, interaction.guild_id)
        if rowifi_user.is_verified:
            embed.add_field(
                name="Roblox Information",
                value=f"**Name:** {rowifi_user.roblox_user.name}\n"\
                      f"**ID:** {rowifi_user.roblox_user.id}\n"\
                      f"**Created At:** {format_dt(rowifi_user.roblox_user.created_at)}",
                inline=False
            )
            embed.set_thumbnail(url=rowifi_user.roblox_user.headshot_url)
            view = discord.ui.View(timeout=None)
            view.add_item(discord.ui.Button(style=discord.ButtonStyle.link, label="Roblox Profile", url=rowifi_user.roblox_user.profile_url))

        else:
            embed.description += "\nCannot fetch ROBLOX Profile as this user is not verified with RoWifi."
            embed.set_thumbnail(url=user.display_avatar.url)
            view = discord.utils.MISSING

        def guild_info() -> str:
            info = ''
            if isinstance(user, discord.Member):
                roles = user.roles
                roles.remove(interaction.guild.default_role)
                if roles:
                    string = ', '.join([r.mention for r in roles]) if len(roles) <= 7 else f'{len(roles)} roles'
                else:
                    string = ''

                info = f'**Joined At:** {format_dt(user.joined_at)}\n**Roles:** {string}'
            else:
                embed.description = "*This user is not in the current server.*"
            return info

        embed.add_field(
            name="Discord Information",
            value=f"**Name:** {user.display_name}\n"\
                  f"**ID:** {user.id}\n"\
                  f"**Created At:** {format_dt(user.created_at)}\n"\
                  f"{guild_info()}",
            inline=False
        )
        if not embed.description:
            embed.description = None

        await interaction.response.send_message(embed=embed, view=view)

    @is_bot_channel()
    @app_commands.command(name="user-in-group", description="Checks if a user is in a ROBLOX Group.")
    @app_commands.describe(user="The user tho check for", group_id="The id of the group to check in for.", userid="The roblox user id to looks for.", username="Roblox user name to look for.")
    async def uig(self, interaction: discord.Interaction, user: Optional[discord.User], userid: Optional[int], username: Optional[str], group_id: int) -> None:
        user_id = None
        session = self.bot.session
        if user:
            data = await request(session, 'GET', ROWIFIAPI.format(user.id, interaction.guild_id))
            if data['success']:
                user_id = data['roblox_id']
        elif userid:
            user_id = userid
        elif username:
            data = await request(session, 'POST', 'https://users.roblox.com/v1/usernames/users', data={'usernames':[username]})
            if data['data']:
                user_id = data['data'][0]['id']
        
        if user_id is None:
            return await interaction.response.send_message(f"Cannot find the ROBLOX Profile of user `{user or userid or username}`.")

        if self.__member_cache.get(f'{user_id}-{group_id}'):
            member: Member = self.__member_cache[f'{user_id}-{group_id}']
            return await interaction.response.send_message(
                f"{member.name} is in the group with id `{group_id}`. (Role: {member.role.name})"
            )

        ro_user = await self.get_user(user_id)
        group_data = await request(session, 'GET', f'https://groups.roblox.com/v2/users/{user_id}/groups/roles')
        for group in group_data['data']:
            if group['group']['id'] == group_id:
                member = Member(ro_user._raw_data, group['role'], group_id)
                self.__member_cache[f'{user_id}-{group_id}'] = member
                return await interaction.response.send_message(
                    f"{member.name} is in the group with id `{group_id}`. (Role: {member.role.name})"
                )

        return await interaction.response.send_message(f"{ro_user.name} is not in the group with id `{group_id}`.")

    async def send_paginator(self, interaction: discord.Interaction, content: str) -> None:
        pages = TextPages(content, prefix="```json\n", interaction=interaction, bot=self.bot)
        await pages.start()

    async def custom_cooldown(interaction: discord.Interaction) -> Optional[app_commands.Cooldown]:
        pre = (
            await check_perms(interaction, {'manage_messages':True}) or
            await has_setting_role(interaction, 'bypass')
        )

        if pre:
            return None
        return app_commands.Cooldown(1, 5.0)

    @is_bot_channel()
    @app_commands.checks.dynamic_cooldown(custom_cooldown, key=lambda interaction: interaction.guild.id)
    @app_commands.command(name="raw-message", description="Gives out the raw json of the message.")
    @app_commands.describe(channel="The channel the message belongs to.", message_id="The id of the message.")
    async def rawmsg(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel], message_id: str) -> None:
        channel = channel or interaction.channel
        try:
            response = await self.bot.http.get_message(channel.id, int(message_id))
        except Exception as e:
            return await interaction.response.send_message(str(e), ephemeral=True)
        else:
            data = json.dumps(response, indent=4)
            await self.send_paginator(interaction, data)

    raw = app_commands.Group(name="raw", description="Parent of raw api searches")

    async def get_json_content(self, url: str) -> str:
        data = await request(self.bot.session, 'GET', url)
        return json.dumps(data, indent=4)

    @is_bot_channel()
    @app_commands.checks.dynamic_cooldown(custom_cooldown, key=lambda interaction: interaction.guild.id)
    @raw.command(name="api", description="Gives JSON content of the GET Method used on the api.")
    @app_commands.describe(url="The API url to lookup.")
    async def api(self, interaction: discord.Interaction, url: str) -> None:
        content = await self.get_json_content(url)
        await self.send_paginator(interaction, content)

    @is_bot_channel()
    @app_commands.checks.dynamic_cooldown(custom_cooldown, key=lambda interaction: interaction.guild.id)
    @raw.command(name="group-roles", description="Gives the JSON content of the ROBLOX Group's roles.")
    @app_commands.describe(group_id="The id of the group.")
    async def group_roles(self, interaction: discord.Interaction, group_id: int) -> None:
        content = await self.get_json_content(GROUP.format('v1', f'groups/{group_id}/roles'))
        await self.send_paginator(interaction, content)

    @is_bot_channel()
    @app_commands.checks.dynamic_cooldown(custom_cooldown, key=lambda interaction: interaction.guild.id)
    @raw.command(name="group", description="Gives the JSON content of the ROBLOX Group.")
    @app_commands.describe(group_id="The id of the group.")
    async def group(self, interaction: discord.Interaction, group_id: int) -> None:
        content = await self.get_json_content(GROUP.format('v1', f'groups/{group_id}'))
        await self.send_paginator(interaction, content)

    @is_bot_channel()
    @app_commands.checks.dynamic_cooldown(custom_cooldown, key=lambda interaction: interaction.guild.id)
    @raw.command(name="user", description="Gives the JSON content of the ROBLOX User.")
    @app_commands.describe(user_id="The id of the user.")
    async def user(self, interaction: discord.Interaction, user_id: int) -> None:
        content = await self.get_json_content(USER.format(user_id))
        await self.send_paginator(interaction, content)

    @is_bot_channel()
    @app_commands.checks.dynamic_cooldown(custom_cooldown, key=lambda interaction: interaction.guild.id)
    @raw.command(name="user-roles", description="Gives the JSON content of the ROBLOX User roles in different groups.")
    @app_commands.describe(user_id="The id of the user.")
    async def user_roles(self, interaction: discord.Interaction, user_id: int) -> None:
        content = await self.get_json_content(GROUP.format('v2', f'users/{user_id}/groups/roles'))
        await self.send_paginator(interaction, content)

    @app_commands.command(name="tickets", description="For internal management of the tickets bot.")
    @app_commands.describe(member="To show tickets for a specific user. (Available to admins only.)")
    async def tickets(self, interaction: discord.Interaction, member:Optional[discord.Member]) -> None:
        await interaction.response.send_message(f"Loading...")
        ctx = await self.bot.get_context(interaction, cls=Context)
        if member is None and interaction.user.guild_permissions.administrator:
            member = None
        elif interaction.user.guild_permissions.administrator:
            member = member or interaction.user
        else:
            member = interaction.user

        now = discord.utils.utcnow()
        reference = None
        last = None
        total = []
        unclaimed = []

        if now.month == 1:
            after = now.replace(month=12)
        else:
            after = now.replace(month=now.month-1)

        settings = await self.bot.get_guild_settings(interaction.guild_id)
        if settings.tickets_channel is None:
            return await interaction.edit_original_message(content="No ticket category has been set for.", ephemeral=True)
        channel = interaction.guild.get_channel(settings.tickets_channel)
        if channel is None:
            try:
                channel = await interaction.guild.fetch_channel(settings.tickets_channel)
            except:
                return await interaction.edit_original_message(content="Fetching the channel failed!")
        url_regex = re.compile('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', re.IGNORECASE)
        async for message in channel.history(limit=None, after=after):
            if message.embeds and message.author.id == 508391840525975553:
                embed = message.embeds[0]
                ticket_id = embed.fields[0].value
                claimed_by = embed.fields[-2].value

                try:
                    transcript = message.components[0].children[0].url
                except:
                    transcript = url_regex.findall(embed.fields[-3].value)[0]

                if transcript is None:
                    transcript = url_regex.findall(embed.fields[-3].value)[0]

                if reference is None:
                    reference = message

                last = message

                if member is None:
                    total.append(f'[Ticket #{ticket_id}]({transcript}) - {claimed_by}')
                    if claimed_by.casefold() == 'not claimed':
                        unclaimed.append(f"[Ticket #{ticket_id}]({transcript})")
                else:
                    try:
                        staff = await commands.UserConverter().convert(ctx, claimed_by)
                    except:
                        pass
                    else:
                        if staff.id == member.id:
                            total.append(f'[Ticket #{ticket_id}]({transcript})')
        if len(total) == 0:
            return await interaction.edit_original_message(content="No tickets to show.")
        if member is None:
            claimed = len(total) - len(unclaimed)
            title = f"Claimed: {claimed}/{len(total)} (Unclaimed: {len(unclaimed)})"
        else:
            title = f"Tickets handled"

        embed = Embed(
            bot=self.bot,
            title=title
        )

        embed.add_field(
            name="Tickets taken from",
            value=f"**[From:]({reference.jump_url})** {format_dt(after)}\n"\
                  f"**[Until:]({last.jump_url})** {format_dt(now)}",
            inline=False
        )
        pages = TicketPages(total, interaction=interaction, bot=self.bot, embed=embed)
        await pages.start()
        
        # if unclaimed and member is None:
        #     embed.title = "Unclaimed Tickets!"
        #     unclaimed_pages = TicketPages(unclaimed, interaction=interaction, bot=self.bot, per_page=15, embed=embed)
        #     await unclaimed_pages.start()


async def setup(bot: Bot):
    await bot.add_cog(Information(bot))
