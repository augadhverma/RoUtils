from typing import Optional, Union
import discord

from discord.ext import commands
from datetime import datetime
from string import ascii_letters
from random import choice

from utils.db import Connection
from utils.checks import staff, senior_staff, council
from utils.classes import DiscordUser, InfractionType, EmbedInfractionType, EmbedLog, InfractionColour, InfractionEmbed

from cogs.tags import Tags

class Moderation(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        self.mod_db = Connection("Utilities","Infractions")

    async def get_or_fetch_user(self, id:int):
        user = self.bot.get_user(id)
        if user:
            return user
        user = self.bot.fetch_user(id)
        return user
    
    async def get_id(self) -> int:
        data = self.mod_db.find({})
        collection = []
        
        async for doc in data:
            collection.append(doc)
        if not collection:
            return 1
        latest = collection.pop()
        return latest['id']+1

    def embed_builder(self, type:InfractionType,**kwargs) -> discord.Embed:
        title = kwargs['title']
        offender = kwargs.get("offender")
        moderator = kwargs.get("moderator")
        reason = kwargs.get("reason")
        id = kwargs.get("id")

        embed = discord.Embed(
            colour = InfractionColour[type.name].value,
            timestamp = datetime.utcnow()
        )
        embed.set_footer(text=self.bot.footer)

        embed.title = f"{title} | Case #{id}"
        embed.set_thumbnail(url=offender.avatar_url)
        embed.description = f"**Offender:** {offender.mention} `({offender.id})`\n**Reason:** {reason}\n**Moderator:** {moderator.mention} `({moderator.id})`"
        return embed


    async def append_infraction(self, type:InfractionType, offender:Union[discord.User, discord.Member], moderator:discord.Member, reason:str,time:datetime=None) -> dict:
        document = {
            "id":await self.get_id(),
            "type":int(type),
            "offender":offender.id,
            "moderator":moderator.id,
            "reason":reason,
            "time":time
        }

        await self.mod_db.insert_one(document)
        return document

    async def delete_infraction(self, id:str) -> dict:
        document = await self.mod_db.find_one_and_delete({"id":{"$eq":id}})
        return document

    @staff()
    @commands.command()
    async def warn(self, ctx:commands.Context, offender:discord.Member, *,reason:commands.clean_content):
        """Warns a user"""

        doc = await self.append_infraction(
            InfractionType.warn,
            offender,
            ctx.author,
            reason
        )

        await ctx.send("\U0001f44c")

        embed = self.embed_builder(
            type= InfractionType.warn,
            title = InfractionType.warn.name,
            offender = offender,
            moderator = ctx.author,
            reason = reason,
            id = doc['id']
        )

        await EmbedLog(ctx, embed).post_log()

    @staff()
    @commands.command()
    async def warns(self, ctx:commands.Context, user:Optional[discord.Member]):
        """Shows warns of a user or everyone"""
        container = []
        if not user:
            infs = self.mod_db.find({})
            async for inf in infs:
                container.append(inf)
            if not container:
                return await ctx.send("The server is squeaky clean. <:noice:811536531839516674> ")
        elif user:
            infs = self.mod_db.find({"offender":{"$eq":user.id}})
            async for inf in infs:
                container.append(inf)

            if not container:
                return await ctx.send(f"**{user}** is squeaky clean. <:noice:811536531839516674> ")
        embed = await InfractionEmbed(ctx, container).embed_builder()
        await ctx.send(embed=embed)

    @staff()
    @commands.command()
    async def rw(self, ctx:commands.Context, id:int, *,reason:str):
        document = await self.delete_infraction(id)
        if document:
            await ctx.send("\U0001f44c")
        else:
            return await ctx.send("\U0001f44e")

        type = InfractionType(document['type']).name

        inf_id = document['id']

        embed = discord.Embed(
            title = f"Infraction Removed ({type} | Case #{inf_id})",
            colour = discord.Color.greyple(),
            timestamp=datetime.utcnow()
        )

        moderator = await DiscordUser().convert(ctx, str(document['moderator']))
        offender = await DiscordUser().convert(ctx, str(document['offender']))

        embed.description = f"**Offender:** {offender.mention} `({offender.id})`\n**Reason:** {document['reason']}\n**Moderator:** {moderator.mention} `({moderator.id})`"

        embed.add_field(
            name="Removed by",
            inline=False,
            value=f"{ctx.author.mention} `({ctx.author.id})`"
        )
        
        embed.add_field(
            name="Reason for Removal",
            value=reason
        )


        embed.set_thumbnail(url=offender.avatar_url)
        embed.set_footer(text=self.bot.footer)
        await EmbedLog(ctx, embed).post_log()
        


def setup(bot):
    bot.add_cog(Moderation(bot))