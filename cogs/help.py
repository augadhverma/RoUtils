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

from inspect import signature
import discord
from discord.ext import commands
from datetime import date, datetime

class CustomHelp(commands.HelpCommand):
    def __init__(self, colour, footer):
        self.colour = colour
        self.footer = footer
        super().__init__(command_attrs={
            "help":"Shows the help message",
            "aliases":["h","cmd","cmds","commands"],
            "usage":"[command]"
        })

    async def send_bot_help(self, mapping):
        embed = discord.Embed(
            title="Help",
            colour=self.colour,
            timestamp=datetime.utcnow(),
            description=f"Type `{self.context.prefix}help [command/module]` for info on a command or a module"
        )
        for cog, cmds in mapping.items():
            if cog and len(cmds)!=0:
                filtered = await self.filter_commands(cmds, sort=True)
                if len(filtered)!=0:
                    try:
                        embed.add_field(name=cog.qualified_name, value=", ".join([f"`{c.name}`" for c in filtered]),inline=False)
                    except:
                        pass
        embed.set_footer(text=self.footer)
        await self.get_destination().send(embed=embed)



    async def send_cog_help(self, cog):
        embed = discord.Embed(
            title=f"Help on {cog.qualified_name}",
            colour=self.colour,
            timestamp=datetime.utcnow()
        )
        if cog.description:
            embed.description = cog.description

        filtered = await self.filter_commands(cog.get_commands(), sort=True)
        for cmd in filtered:
            try:
                embed.add_field(
                    name=cmd.qualified_name,
                    value=cmd.help if cmd.help else "No help provided...",
                    inline=False
                )
            except:
                pass
        embed.set_footer(text=self.footer)
        await self.get_destination().send(embed=embed)

    async def send_command_help(self, cmd):
        embed = discord.Embed(
            title = f"Help for command: {cmd}",
            colour = self.colour,
            timestamp = datetime.utcnow(),
            description = cmd.help if cmd.help else "No help provided..."
        )

        embed.set_footer(text=self.footer)

        if isinstance(cmd, commands.Group):
            filtered = await self.filter_commands(cmd.commands, sort=True)
            embed.add_field(name="Subcommands", value=", ".join([f"`{c}`" for c in filtered]), inline=False)
        
        if len(cmd.aliases) != 0:
            embed.add_field(name="Aliases", value=", ".join([f"`{c}`" for c in cmd.aliases]), inline=False)

        embed.add_field(
            name="Usage",
            value=f"`{self.context.prefix}{cmd.qualified_name} {cmd.signature}`" if cmd.signature else f"`{self.context.prefix}{cmd.qualified_name}`",
            inline=False
        )

        await self.get_destination().send(embed=embed)

    send_group_help = send_command_help

    async def send_error_message(self, error):
        embed = discord.Embed(title="An Error Occurred", colour=discord.Color.red(), timestamp=datetime.utcnow())
        embed.description = str(error)
        embed.set_footer(text=self.footer)
        await self.get_destination().send(embed=embed)


class MyHelp(commands.Cog, name="Help"):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        bot.help_command = CustomHelp(colour=self.bot.colour, footer=self.bot.footer)

def setup(bot:commands.Bot):
    bot.add_cog(MyHelp(bot))
