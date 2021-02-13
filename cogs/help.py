import discord
from discord.ext import commands
from datetime import datetime
from typing import Mapping, Union

class CustomHelp(commands.HelpCommand):
    def __init__(self, colour, footer:str):
        self.colour = colour
        self.footer = footer

        super().__init__(
            command_attrs={
                'help':'Shows help message',
                'usage':'[command]'
            }
        )

    def get_command_usage(self, command:Union[commands.Command, commands.Group]) -> str:
        return f"{command.qualified_name} {command.signature}"

    async def send_bot_help(self, mapping:Mapping):
        embed = discord.Embed(
            colour = self.colour,
            title="Help",
            description=f"Type `{self.clean_prefix}help [command/category]` for more info on a command or a category.",
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=self.footer)

        for cog, cmds in mapping.items():
            if cog and cmds:
                f = await self.filter_commands(cmds, sort=True)
                if f:
                    try:
                        embed.add_field(
                            name=cog.qualified_name,
                            value=f", ".join([f"`{c.name}`" for c in f]),
                            inline=False
                        )
                    except:
                        pass
        await self.get_destination().send(embed=embed)

    
    async def send_command_help(self, command:Union[commands.Command, commands.Group]):
        embed = discord.Embed(
            title="Help",
            description=f"{command.name}: {command.help if command.help else 'No help provided...'}",
            colour=self.colour,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=self.footer)

        embed.add_field(
            name="Usage",
            value=f"`{self.get_command_usage(command)}`",
            inline=False
        )

        if command.aliases:
            embed.add_field(
                name="Aliases",
                value=", ".join([f"`{c}`" for c in command.aliases]),
                inline=False
            )

        if isinstance(command, commands.Group):
            f = await self.filter_commands(command.commands, sort=True)
            embed.add_field(
                name="Subcommands",
                value=", ".join([f"`{c.name}`" for c in f]),
                inline=False
            )

        await self.get_destination().send(embed=embed)


    send_group_help = send_command_help

    async def send_cog_help(self, cog:commands.Cog):
        embed = discord.Embed(
            title=f"{cog.qualified_name} Commands",
            colour=self.colour,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=self.footer)

        if cog.description:
            embed.description = cog.description
        f = await self.filter_commands(cog.get_commands(), sort=True)
        for cmd in f:
            try:
                embed.add_field(
                    name=self.get_command_usage(cmd),
                    value=f"{cmd.help if cmd.help else 'No help provided...'}",
                    inline=False
                )
            except:
                pass

        await self.get_destination().send(embed=embed)

    async def send_error_message(self, error):
        await self.get_destination().send(error)

class MyHelp(commands.Cog, name="Help"):
    def __init__(self, bot:commands.Bot) -> None:
        self.bot = bot
        bot.help_command = CustomHelp(self.bot.colour, self.bot.footer)

def setup(bot:commands.Bot):
    bot.add_cog(MyHelp(bot))