"""
Bot configuration related.

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

import asyncio
import discord
import random

from discord.ext import commands, tasks
from bot import RoUtils, extensions

from datetime import datetime
from typing import Union

from utils.checks import admin, botchannel

class Config(commands.Cog):
    def __init__(self, bot:RoUtils) -> None:
        self.bot = bot
        self.db = bot.utils
        self.status_loop.start()

    @commands.is_owner()
    @commands.command()
    async def reload(self, ctx:commands.Cog, *,name:str):
        """ reloads a/all file(s). """
        if name == '~':
            ext = []
            for f in extensions:
                try:
                    self.bot.reload_extension(f)
                    ext.append(f)
                    print(f'Reloaded {f} at {datetime.utcnow()}')
                except Exception as e:
                    await ctx.send(f'```py\n{e}```')
            embed = discord.Embed(
                title="Successfully reloaded the following extensions:",
                description = "\n".join(e for e in ext),
                colour = self.bot.invisible_colour
            )
            return await ctx.reply(embed=embed)

        else:
            try:
                self.bot.reload_extension(f"{name}")
                print(f'Reloaded {name} at {datetime.utcnow()}')
            except Exception as e:
                return await ctx.send(f"```py\n{e}```")
            await ctx.reply(f"Successfully reloaded: **`{name.replace('.','/')}.py`**")

    @commands.is_owner()
    @commands.command()
    async def load(self, ctx:commands.Context, *,name:str):
        """Loads a cog."""
        try:
            self.bot.load_extension(f"{name}")
            print(f'Loaded {name} at {datetime.utcnow()}')
        except Exception as e:
            return await ctx.send(f"```py\n{e}```")
        await ctx.send(f"📥 Loaded extension: **`{name.replace('.','/')}.py`**")

    @commands.is_owner()
    @commands.command()
    async def unload(self, ctx:commands.Context, *,name:str):
        """Unloads a cog."""
        try:
            self.bot.unload_extension(f"{name}")
            print(f'Unloaded {name} at {datetime.utcnow()}')
        except Exception as e:
            return await ctx.send(f"```py\n{e}```")
        await ctx.send(f"📤 Unloaded extension: **`{name.replace('.','/')}.py`**")

    def status(self) -> discord.Status:
        return random.choice([
            discord.Status.online,
            discord.Status.dnd,
            discord.Status.idle
        ])
        
    async def get_activity(self, *, All=False) -> Union[discord.Activity, list]:
        activities = (await self.db.find_one({'name':'activities'}))['activities']
        if All:
            return activities
        else:
            choice = random.choice(activities)
            return discord.Activity(
                type = discord.ActivityType[choice[0]],
                name = choice[1]
            )
        
    
    @tasks.loop(minutes=5.0)
    async def status_loop(self) -> None:
        status = self.status()
        activity = await self.get_activity()
        
        await self.bot.change_presence(activity=activity, status=status)
        
    @status_loop.before_loop
    async def before_status_loop(self):
        await self.bot.wait_until_ready()
        
    async def update_activities(self, type, name, *, remove=False):
        """Updates the activities in the database.

        Args:
            type (str): The type of activity to use. Refere `discord.ActivityType`
            name (str): The name of the activity to display.
            remove (bool, optional): Whether removing or appending to the database. Defaults to False.

        Returns:
            pymongo.results.UpdateResult: The updated document.
        """
        document = await self.db.find_one({'name':'activities'})
        
        L:list = document['activities']
        
        if remove:
            for a in L:
                if name == a[1]:
                    L.remove(a)
                    break
        else:
            for a in L:
                if name == a[1] and type == a[0]:
                    return
                else:
                    L.append((type, name))
                    break
                    
        return await self.db.update_one(
            {'name':'activities'},
            {'$set':dict(activities=L)}
        )

    
    @admin()
    @commands.group(name='activity')
    async def activity(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(self.activity)
         
    @admin()
    @activity.command(name='set', invoke_without_command=True)
    async def set_activity(self, ctx:commands.Context, type:str, *, string:str):
        """ Sets an activity. Valid types are:
            - playing
            - listening
            - competing
            - watching"""
        status = ctx.me.status
        valid = ('playing', 'listening', 'watching', 'competing')
        if type not in valid:
            return await ctx.send(f'Invalid type provided. Please choose from: {valid}')
        await self.bot.change_presence(
            status = status,
            activity = discord.Activity(
                type = discord.ActivityType[type],
                name = string
            )
        )
        
        await ctx.message.add_reaction('<:tick:818793909982461962>')
        
    @admin()
    @activity.command(name='add')
    async def add_activity(self, ctx:commands.Context, type:str, *, string:str):
        """ Adds an activity to the database so it can loop over."""
        
        valid = ('playing', 'listening', 'watching', 'competing')
        if type not in valid:
            return await ctx.send(f'Invalid type provided. Please choose from: {valid}')
        
        await self.update_activities(type=type, name=string)
        
        await ctx.message.add_reaction('<:tick:818793909982461962>')
        
    @admin()
    @activity.command(name='remove')
    async def remove_activityy(self, ctx:commands.Context, *, name:str):
        """ Removes an activity from the database. """
        
        await self.update_activities(type=type, name=name, remove=True)
        
        await ctx.message.add_reaction('<:tick:818793909982461962>')
        
    @botchannel()
    @activity.command(name='list')
    async def list_activity(self, ctx:commands.Context):
        L = await self.get_activity(All=True)
        
        embed = discord.Embed(
            colour = self.bot.invisible_colour,
            timestamp = datetime.utcnow()
        )
        embed.description = "\n".join([f'{i}. `{n}`' for i,n in enumerate(L, 1)])
        embed.set_footer(text='All statuses queued for bot status (Not in any order).')
        
        msg = await ctx.send(embed = embed)
        
        await msg.add_reaction('\N{INFORMATION SOURCE}\ufe0f')
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == '\N{INFORMATION SOURCE}\ufe0f'
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            pass
        else:
            url = 'https://discordpy.readthedocs.io/en/latest/api.html#discord.ActivityType'
            embed.add_field(
                name = "Information is listed in the following format",
                value = f"[[`discord.ActivityType`]({url}), `name`]"
            )
            await msg.edit(contetnt=None, embed=embed)
        finally:
            await msg.clear_reaction('\N{INFORMATION SOURCE}\ufe0f')
            
    @admin()
    @commands.command(name='status')
    async def set_status(self, ctx:commands.Context, * ,status:str):
        """ Sets bot's status.
        
        Valid options:
            - online
            - dnd
            - idle
        """
        valid = ('online', 'dnd', 'idle')
        if status not in valid:
            return await ctx.send(f'Invalid option provided. Valid options are: {valid}')
        
        await self.bot.change_presence(
            activity = ctx.me.activity,
            status = discord.Status[status]
        )
        
        await ctx.message.add_reaction('<:tick:818793909982461962>')

        
def setup(bot:RoUtils):
    bot.add_cog(Config(bot))