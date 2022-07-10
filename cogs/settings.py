"""
The settings module.
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

from typing import Literal, Optional, Union
from discord.ext import commands, tasks
from discord import app_commands
from utils import Bot, Context, Embed, SimplePages, is_admin

SNOWFLAKE_TYPE = Literal['role', 'user', 'channel']

class Settings(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        

    @commands.command(name="sync")
    @commands.is_owner()
    async def sync_command(self, ctx: Context, g: int=0) -> None:
        if g == 1:
            await self.bot.tree.sync(guild=ctx.guild)
        else:
            await self.bot.tree.sync()
        await ctx.send("👌")

    @commands.command()
    @commands.is_owner()
    async def copy(self, ctx: Context) -> None:
        guild = ctx.guild
        self.bot.tree.copy_global_to(guild=guild)
        await ctx.send("👌")

    settings_group = app_commands.Group(name="settings", description="The bot's settings for the current server.")

    @is_admin()
    @settings_group.command(name="view", description="To view the server settings for the current server.")
    async def settings_view(self, interaction: discord.Interaction) -> None:
        settings = await self.bot.get_guild_settings(interaction.guild_id)

        embed = Embed(
            bot=self.bot,
            title="Settings",
            description="Please note that the prefixes work only for some commands."
        )

        bot_log, msg_log = settings.log_channels.values()
        admin, bypass = settings.extra_roles.values()

        def value(title: str, id: int | None, type: SNOWFLAKE_TYPE = None, sep: str = '-') -> str:
            string = f"{title} {sep}"
            if id is None:
                return f"{string} Not Set"
            
            char = ''
            if type == 'channel':
                char = '#'
            elif type == 'role':
                char = '@&'
            elif type == 'user':
                char = '@'

            return f"{string} <{char}{id}>"

        embed.add_field(name="Prefixes", value=f"1. {self.bot.user.mention}\n2. {settings.prefix}")
        embed.add_field(
            name="Log Channels",
            value="\n".join([value('Bot', bot_log, 'channel'), value('Message', msg_log, 'channel')])
        )
        embed.add_field(
            name="Extra Roles",
            value="\n".join(
                [
                    value('Admin', admin, 'role'),
                    value('Bypass', bypass, 'role')
                ]
            )
        )
        embed.add_field(
            name="Commands Disabled in",
            value="\n".join(f"{i}. <#{c}>" for i, c in enumerate(settings.command_disabled_channels, 1)) or "Not Set"
        )
        embed.add_field(
            name="Detection Disabled in",
            value="\n".join(f"{i}. <#{c}>" for i, c in enumerate(settings.detection_exclusive_channels, 1)) or "Not Set"
        )
        embed.add_field(name="Mute Role", value=f'<@&{settings.mute_role}>' if settings.mute_role else "Not Set")
        embed.add_field(name="Domain Detection", value=str(settings.domain_detection))
        embed.add_field(name="Bad Word Detection", value=str(settings.bad_word_detection))
        embed.add_field(name="Use Timeout", value=str(settings.timeout_instead_of_mute))

        await interaction.response.send_message(embed=embed)

    @is_admin()
    @settings_group.command(name="actions", description="Set various actions.")
    @app_commands.describe(
        option='The option to set.',
        value='The value to set it to.'
    )
    async def actions(
        self,
        interaction: discord.Interaction,
        option: Literal['Domain Detection', 'Bad Word Detection', 'Use Timeout Instead of Mute'],
        value: Literal['True', 'False']
    ) -> None:
        settings = await self.bot.get_guild_settings(interaction.guild_id)

        if value == 'True':
            value = True
        else:
            value = False

        if option == 'Domain Detection':
            doc_option = 'domainDetection'
        elif option == 'Bad Word Detection':
            doc_option = 'badWordDetection'
        elif option == 'Use Timeout Instead of Mute':
            doc_option = 'timeoutInsteadOfMute'
        
        await self.bot.settings.update_one({'_id':settings.id}, {'$set':{doc_option:value}})

        embed = Embed(
            bot=self.bot,
            colour=discord.Colour.green(),
            title='Success',
            description=f'**{option}** successfully set to `{value}`.'
        )

        await interaction.response.send_message(embed=embed)

    @is_admin()
    @settings_group.command(name='set-log-channels', description='Sets the log channels.')
    @app_commands.describe(type='Bot - Bot Actions | Message - Message Logs', channel='The channel to be set as log channel.')
    async def log_channel(
        self,
        interaction: discord.Interaction,
        type: Literal['Bot', 'Message'],
        channel: discord.TextChannel
    ) -> None:
        settings = await self.bot.get_guild_settings(interaction.guild_id)

        document = {
            'bot':settings.log_channels['bot'],
            'message':settings.log_channels['message']
        }

        document[type.lower()] = channel.id

        await self.bot.settings.update_one({'_id':settings.id}, {'$set':{'logChannels':document}})

        embed = Embed(
            bot=self.bot,
            title='Success',
            colour=discord.Colour.green(),
            description=f'Successfully set **{type} Log Channel** to {channel.mention}.'
        )
        await interaction.response.send_message(embed=embed)

    @is_admin()
    @settings_group.command(name='set-extra-roles', description='Sets the extra roles for the server.')
    @app_commands.describe(type='Which extra role is being set', role='The role to be set.')
    async def extra_roles(
        self,
        interaction: discord.Interaction,
        type: Literal['Admin', 'Bypass'],
        role: discord.Role
    ) -> None:
        settings = await self.bot.get_guild_settings(interaction.guild_id)

        document = {
            'admin':settings.extra_roles['admin'],
            'bypass':settings.extra_roles['bypass']
        }

        document[type.lower()] = role.id

        await self.bot.settings.update_one({'_id':settings.id}, {'$set':{'extraRoles':document}})

        embed = Embed(
            bot=self.bot,
            title='Success',
            colour=discord.Colour.green(),
            description=f'Successfully set **{type} Role** to {role.mention}.'
        )

        await interaction.response.send_message(embed=embed)

    @is_admin()
    @settings_group.command(name='command-channel', description='Enables or Disables the command in the current channel.')
    @app_commands.describe(option='Toggle to enable/disable commands in the current channel.')
    async def command_channel(self, interaction: discord.Interaction, option: Literal['Enable', 'Disable']) -> None:
        settings = await self.bot.get_guild_settings(interaction.guild_id)

        value = True if option == 'Enable' else False
        option = 'enabled' if value else 'disabled'
        channel = interaction.channel_id

        if not value:
            if channel in settings.command_disabled_channels:
                pass
            else:
                settings.command_disabled_channels.append(channel)
        else:
            if channel in settings.command_disabled_channels:
                settings.command_disabled_channels.remove(channel)
        
        await self.bot.settings.update_one({'_id':settings.id}, {'$set':{'commandDisabledChannels':settings.command_disabled_channels}})

        embed = Embed(
            bot=self.bot,
            title='Success',
            colour=discord.Colour.green(),
            description=f'Successfully **{option}** commands in {interaction.channel.mention}.'
        )

        await interaction.response.send_message(embed=embed)

    @is_admin()
    @settings_group.command(name='detection', description="Disabled detection of links or bad words in the current channel.")
    @app_commands.describe(option='Toggle to enable/disable detection in the current channel.')
    async def detection(
        self,
        interaction: discord.Interaction,
        option: Literal['Enable', 'Disable'],
        channel: Optional[Union[discord.TextChannel, discord.CategoryChannel]]
    ) -> None:
        settings = await self.bot.get_guild_settings(interaction.guild_id)

        value = True if option == 'Enable' else False
        option = 'enabled' if value else 'disabled'
        channel = channel or interaction.channel

        if not value:
            if channel.id in settings.detection_exclusive_channels:
                pass
            else:
                settings.detection_exclusive_channels.append(channel.id)
        else:
            if channel.id in settings.detection_exclusive_channels:
                settings.detection_exclusive_channels.remove(channel.id)

        await self.bot.settings.update_one({'_id':settings.id}, {'$set':{'detectionExclusiveChannels':settings.detection_exclusive_channels}})

        embed = Embed(
            bot=self.bot,
            title='Success',
            colour=discord.Colour.green(),
            description=f'Successfully **{option}** detecion in {channel.mention}.'
        )

        await interaction.response.send_message(embed=embed)

    @is_admin()
    @settings_group.command(name="mute-role", description="Set a mute role for the server.")
    @app_commands.describe(role="The role to set as mute role.")
    async def mute_role(self, interaction: discord.Interaction, role: discord.Role) -> None:
        settings = await self.bot.get_guild_settings(interaction.guild_id)

        await self.bot.settings.update_one({'_id':settings.id}, {'$set':{'muteRole':role.id}})

        embed = Embed(
            bot=self.bot,
            title="Success",
            colour=discord.Colour.green(),
            description=f"Mute role successfully set to {role.mention}."
        )

        await interaction.response.send_message(embed=embed)

    @is_admin()
    @settings_group.command(name="prefix", description="Changes the prefix of the bot for the server.")
    @app_commands.describe(prefix="The prefix to be set.")
    async def set_prefix(self, interaction: discord.Interaction, prefix: str) -> None:
        settings = await self.bot.get_guild_settings(interaction.guild_id)

        await self.bot.settings.update_one({'_id':settings.id}, {'$set':{'prefix':prefix}})

        embed = Embed(
            bot=self.bot,
            title="Success",
            colour=discord.Colour.green(),
            description=f"Server prefix successfully set to `{prefix}`."
        )

        await interaction.response.send_message(embed=embed)

    domain_whitelist = app_commands.Group(
        name="domain-whitelist",
        description="Works with the domains whitelisted for the server.",
        parent=settings_group
    )

    @is_admin()
    @domain_whitelist.command(name="view", description="Shows the domain whitelisted.")
    async def whitelist_view(self, interaction: discord.Interaction) -> None:
        settings = await self.bot.get_guild_settings(interaction.guild_id)

        if settings.domains_whitelisted:
            embed = Embed(
                bot=self.bot,
                title="Domains Whitelisted"
            )
            pages = SimplePages(settings.domains_whitelisted, interaction=interaction, bot=self.bot, embed=embed)
            await pages.start()
        else:
            await interaction.response.send_message("No domains have been whitelisted.")

    @is_admin()
    @domain_whitelist.command(name="add", description="Adds a domain to the server whitelist.")
    @app_commands.describe(domain="The domain to be added to the whitelist.")
    async def whitelist_add(self, interaction: discord.Interaction, domain: str) -> None:
        settings = await self.bot.get_guild_settings(interaction.guild_id)

        if domain in settings.domains_whitelisted:
            return await interaction.response.send_message(f"Domain: `{domain}` is already whitelisted.")

        else:
            settings.domains_whitelisted.append(domain)
            await self.bot.settings.update_one(
                {'_id':settings.id},
                {'$set':{'domainsWhitelisted':settings.domains_whitelisted}}
            )

            embed = Embed(
                bot=self.bot,
                colour=discord.Colour.green(),
                title="Success",
                description=f"Successfully whitelisted `{domain}`."
            )

            await interaction.response.send_message(embed=embed)

    @is_admin()
    @domain_whitelist.command(name="remove", description="Removes a domain from the server whitelist.")
    @app_commands.describe(domain="The domain to be removed from the server whitelist.")
    async def whitelist_remove(self, interaction: discord.Interaction, domain: str) -> None:
        settings = await self.bot.get_guild_settings(interaction.guild_id)

        if domain in settings.domains_whitelisted:
            settings.domains_whitelisted.remove(domain)

            await self.bot.settings.update_one(
                {'_id':settings.id},
                {'$set':{'domainsWhitelisted':settings.domains_whitelisted}}
            )

            embed = Embed(
                bot=self.bot,
                colour=discord.Colour.green(),
                title="Success",
                description=f"Successfully removed the whitelisted domain: `{domain}`."
            )

            await interaction.response.send_message(embed=embed)

        else:
            await interaction.response.send(f"Domain `{domain}` could not be removed since it was not whitelisted.")

    bad_word = app_commands.Group(
        name="bad-words",
        description="Handles server bad words",
        parent=settings_group
    )

    @is_admin()
    @bad_word.command(name="view", description="Shows the bad words in the server.")
    async def bad_word_view(self, interaction: discord.Interaction) -> None:
        settings = await self.bot.get_guild_settings(interaction.guild_id)

        if settings.bad_words:
            embed = Embed(
                bot=self.bot,
                title="Bad Words Registered"
            )
            pages = SimplePages(settings.bad_words, interaction=interaction, bot=self.bot, embed=embed)
            await pages.start()
        else:
            await interaction.response.send_message("No bad words have been registered.")

    @is_admin()
    @bad_word.command(name="add", description="Registers a new bad word.")
    @app_commands.describe(word="The bad word to add.")
    async def bad_word_add(self, interaction: discord.Interaction, word: str) -> None:
        settings = await self.bot.get_guild_settings(interaction.guild_id)

        if word in settings.bad_words:
            return await interaction.response.send_message(f"Word: `{word}` is already registered.")

        else:
            settings.bad_words.append(word)
            await self.bot.settings.update_one(
                {'_id':settings.id},
                {'$set':{'badWords':settings.bad_words}}
            )

            embed = Embed(
                bot=self.bot,
                colour=discord.Colour.green(),
                title="Success",
                description=f"Successfully registered `{word}`."
            )

            await interaction.response.send_message(embed=embed)
    
    @is_admin()
    @bad_word.command(name="remove", description="Removes a bad word from the registered set of words.")
    @app_commands.describe(word="The word to be removed.")
    async def bad_word_remove(self, interaction: discord.Interaction, word: str) -> None:
        settings = await self.bot.get_guild_settings(interaction.guild_id)

        if word in settings.bad_words:
            settings.bad_words.remove(word)

            await self.bot.settings.update_one(
                {'_id':settings.id},
                {'$set':{'badWords':settings.bad_words}}
            )

            embed = Embed(
                bot=self.bot,
                colour=discord.Colour.green(),
                title="Success",
                description=f"Successfully removed the bad word: `{word}`."
            )

            await interaction.response.send_message(embed=embed)

        else:
            await interaction.response.send(f"Word `{word}` could not be removed since it was not registered.")

    
async def setup(bot: Bot) -> None:
    await bot.add_cog(Settings(bot))