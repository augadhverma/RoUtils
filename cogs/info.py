"""
Handles Discord and Roblox related infos.

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

import discord
from discord.ext import commands

from typing import Optional, Union
from datetime import datetime
from utils import roblox, time, cache
from utils.checks import botchannel
from bot import RoUtils

usersCache = cache.TimedCache()


emojis = {
    "partner":"<:rowifipartners:768616388276912138>",
    "staff":"<:staff:768113190462291988>",
    "council":"<:rowificouncil:768616492363022366>",
    "alpha":"<:rowifialphatier:768616726891855943>",
    "beta":"<:rowifibetatier:768616655009611796>",
    "management":"<:management:840086265390694460>"
}

roles = {
    "alpha":680859671560585358,
    "beta":628148318014406657,
    "partner":625384618622976001,
    "staff":652203841978236940,
    "council":626860276045840385,
    "management":671634821323423754
}

class Information(commands.Cog):
    def __init__(self, bot:RoUtils):
        self.bot = bot

    async def is_user_in_group(self, userId:int, groupId:int) -> Union[roblox.Member, None]:
            """Checks if user is in a group or not.

            Parameters
            ----------
            userId : int
                The user'id to check for.
            groupId : int
                The group id to check in.

            Returns
            -------
            Union[Member, None]
                The `roblox.Member` object if found else `None`
            """
            _all = (await self.bot.session.get(f"https://groups.roblox.com/v2/users/{userId}/groups/roles"))
            _all = (await _all.json())['data']
            user = await self.bot.session.get(f'https://users.roblox.com/v1/users/{userId}')
            user = (await user.json())
            for data in _all:
                if data['group']['id'] == groupId:
                    d = {
                        'name':user['name'],
                        'id':userId,
                        'displayName':user['displayName'],
                        'role':{
                            'id':data['role']['id'],
                            'name':data['role']['name'],
                            'rank':data['role']['rank'],
                            'memberCount':0
                        }
                    }
                    return roblox.Member(group_id=groupId, data=d)
            return None

    async def build_info_embed(self, member:discord.Member, roUser:roblox.User) -> discord.Embed:
        embed = discord.Embed(
            title = "User Information",
            colour = self.bot.invisible_colour,
            timestamp = datetime.utcnow(),
            description="Roblox and Discord information about the user."
        )

        embed.set_thumbnail(url=roUser.avatar_url)
        embed.set_footer(text=self.bot.footer)
        embed.add_field(
            name="Roblox Information",
            value=f"**Username:** {roUser.name}\n"\
                  f"**Id:** {roUser.id}\n"\
                  f"**Created:** {time.human_time(dt=roUser.created, minimum_unit='minutes')}\n"\
                  f"[Profile Url]({roUser.profile_url})",
            inline=False
        )

        
        flags = ""
        userroles = ""
        memberroles = [r for r in member.roles if r != member.guild.default_role]
        if len(memberroles) > 8:
            userroles = f"{len(memberroles)} roles"
        else:
            userroles = ", ".join(r.mention for r in memberroles)

        for role in member.roles:
                for k,v in roles.items():
                    if role.id == v:
                        flags+=f"{emojis[k]} "
            

        embed.set_author(name=str(member), icon_url=member.avatar_url)

        embed.add_field(
            name="Guild Information",
            value=f"**Name:** {member.display_name}\n"\
                    f"**Id:** {member.id}\n"\
                    f"**Created:** {time.human_time(dt=member.created_at, minimum_unit='minutes')}\n"\
                    f"**Joined:** {time.human_time(dt=member.joined_at, minimum_unit='minutes')}\n"\
                    f"**Roles:** {userroles}\n"\
                    f"**Flags:** {flags}"
        )

        return embed

    @botchannel()
    @commands.command(aliases=["useringroup"])
    async def uig(self, ctx:commands.Context, user:Union[int, discord.User, str], groupId:int):
        """ Checks if the user is in group or not. """
        userId = 1
        
        if isinstance(user, int):
            userId = user
        
        elif isinstance(user, discord.User):
            response = await self.bot.session.get(f"https://api.rowifi.link/v1/users/{user.id}?guild_id={ctx.guild.id}")
            r = await response.json()
            if r['success']:
                userId = r['roblox_id']
        
        elif isinstance(user, str):
            data = {
                'usernames':[
                    user
                ]
            }
            response = await self.bot.session.post("https://users.roblox.com/v1/usernames/users", data=data)
            r = await response.json()
            if r:
                if len(r['data']):
                    userId = r['data'][0]['id']
                else:
                    return await ctx.send("Can't find a user with the given name.")

        member = await self.is_user_in_group(userId=userId, groupId=groupId)
        if member:
            await ctx.send(f"{member.name} is in the group with id {member.group_id}. They have the role: {member.role.name} (Rank: {member.role.rank})")
        else:
            await ctx.send("The user is not in the given group id.")

    @botchannel()
    @commands.command(aliases=["ui"])
    async def userinfo(self, ctx:commands.Context, member:Optional[Union[discord.Member, discord.User]]):
        """ Gives information on a user. If no user is given, the information is showed of the invokee of the command."""
        member = member or ctx.author

        

        if isinstance(member, discord.Member):
            embed = usersCache.get(member.id, None)
            if embed is None:
                rowifiResponse = await self.bot.session.get(f"https://api.rowifi.link/v1/users/{member.id}?guild_id={ctx.guild.id}")
                rowifi_json = await rowifiResponse.json()

                data = {}

                if not rowifi_json['success']:
                    await ctx.send("\U000026a0 User is not verified with RoWifi!")
                    data = {
                        "name":"JohnDoe",
                        "id":0,
                        "displayName":"JohnDoe",
                        "description":"User is not verifed with RoWifi. Please ask them to do so",
                        "created":datetime.strftime(datetime.utcnow(), '%Y-%m-%dT%H:%M:%S.%fZ'),
                        "banned":None
                    }
                else:
                    roId = rowifi_json['roblox_id']
                    robloxResponse = await self.bot.session.get(f"https://users.roblox.com/v1/users/{roId}")
                    roblox_json = await robloxResponse.json()
                    try:
                        if roblox_json['errors']:
                            data = data
                        else:
                            pass
                    except KeyError:
                        data = roblox_json
                
                roUser = roblox.User(data=data)

                embed = await self.build_info_embed(member=member, roUser=roUser)
                usersCache[member.id] = embed
            
            return await ctx.send(embed=embed)

        elif isinstance(member, discord.User):
            embed = discord.Embed(
                title = "User Information",
                description = "*This user is not in the server.*",
                colour=self.bot.invisible_colour,
                timestamp=datetime.utcnow()
            )
            embed.set_author(name=str(member), icon_url=member.avatar_url)
            embed.add_field(
                name = "ID", value=member.id, inline=False
            )
            embed.add_field(
                name="Created", value=time.human_time(member.created_at),inline=False
            )
            embed.set_footer(text=self.bot.footer)

            return await ctx.send(embed=embed)

    @botchannel()
    @commands.command(aliases=['av'])
    async def avatar(self, ctx:commands.Context, user:Optional[Union[discord.User, discord.Member]]):
        """ Shows avatar of a user. """
        user = user or ctx.author
        embed = discord.Embed(
            title = f"Avatar for {user}",
            timestamp = datetime.utcnow(),
            colour = self.bot.invisible_colour
        )

        embed.set_footer(text=self.bot.footer)
        embed.set_image(url=user.avatar_url)

        embed.add_field(
            name="Link as",
            value=f"[png]({user.avatar_url_as(format='png')}) | [jpg]({user.avatar_url_as(format='jpg')}) | [webp]({user.avatar_url_as(format='webp')})"
        )
        await ctx.send(embed=embed)

def setup(bot:RoUtils):
    bot.add_cog(Information(bot))