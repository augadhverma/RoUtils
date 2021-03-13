import discord

from discord.ext import commands, menus
from datetime import datetime
from typing import Optional, Union
from collections import Counter

from utils.db import Connection
from utils.checks import bot_channel, staff, senior_staff, council, STAFF, COUNCIL
from utils.classes import BanList, DMInfractionEmbed, DiscordUser, InfractionType, EmbedLog, InfractionColour, InfractionEmbed, UserInfractionEmbed, UrlDetection


class Moderation(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        self.mod_db = Connection("Utilities","Infractions")

    def hierarchy_check(self, user:discord.Member, user2:discord.Member) -> bool:
        if user.top_role<=user2.top_role:
            return False
        elif user2.bot:
            return False
        return True
    async def get_or_fetch_user(self, id:int):
        user = self.bot.get_user(id)
        if user:
            return user
        user = await self.bot.fetch_user(id)
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
            "expires":time,
            "added":datetime.utcnow()
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
        await ctx.message.delete()

        if not self.hierarchy_check(ctx.author, offender):
            return await ctx.send("You cannot perform that action due to the hierarchy.")

        doc = await self.append_infraction(
            InfractionType.warn,
            offender,
            ctx.author,
            reason
        )

        await ctx.send(f"Successfully warned **{offender}**. Reason: *{reason}*")

        embed = self.embed_builder(
            type= InfractionType.warn,
            title = InfractionType.warn.name,
            offender = offender,
            moderator = ctx.author,
            reason = reason,
            id = doc['id']
        )

        await EmbedLog(ctx, embed).post_log()

        user_embed = UserInfractionEmbed(InfractionType.warn, reason, doc['id']).embed()
        try:
            await offender.send(embed=user_embed)
        except:
            await ctx.send("Couldn't DM the user since their DMs are closed", delete_after=5.0)

    @staff()
    @commands.group(invoke_without_command=True)
    async def warns(self, ctx:commands.Context, user:Optional[discord.User]):
        """Shows warns of a user or everyone"""
        container = []
        if not user:
            description = ""
            infs = self.mod_db.find({})
            async for inf in infs:    
                container.append(inf['offender'])
            if not container:
                return await ctx.send("The server is squeaky clean. <:noice:811536531839516674> ")
            embed = discord.Embed(
                colour=discord.Color.blurple(),
                title=f"The server has {len(container)} infractions.",
            )
            embed.set_footer(text=f"Run {ctx.prefix}warns <user> for infractions of a particular user.")
            for offender, infractions in Counter(container).items():
                description+=f"{(await self.get_or_fetch_user(offender)).mention} - {infractions} infractions\n"
            embed.description = description
            await ctx.send(embed=embed)

        elif user:
            infs = self.mod_db.find({"offender":{"$eq":user.id}})
            async for inf in infs:
                container.append(inf)

            if not container:
                return await ctx.send(f"**{user}** is squeaky clean. <:noice:811536531839516674> ")
            embed = await InfractionEmbed(ctx, container).embed_builder()
            return await ctx.send(embed=embed)

    @warns.command()
    @staff()
    async def by(self, ctx:commands.Context, moderator:Optional[discord.User]):
        """Shows warns made by a moderator"""
        container = []
        if moderator:
            infs = self.mod_db.find({"moderator":{"$eq":moderator.id}})
            async for inf in infs:
                container.append(inf)
            if not container:
                return await ctx.send(f"**{moderator}** hasn't made any infractions.")
            embed = await InfractionEmbed(ctx, container).embed_builder()
            return await ctx.send(embed=embed)

        else:
            description = ""
            infs = self.mod_db.find({})
            async for inf in infs:
                container.append(inf['moderator'])
            if not container:
                return await ctx.send("No infractions has been made by anyone.")
            embed = discord.Embed(
                colour = discord.Colour.blurple(),
                title = f"This server has {len(container)} infractions."
            )
            embed.set_footer(text=f"Run {ctx.prefix}warns by <user> for infractions given by a particular moderator.")
            for mod, infractions in Counter(container).items():
                description+=f"{(await self.get_or_fetch_user(mod)).mention} has made **{infractions}** infraction(s).\n"
            embed.description = description
            await ctx.send(embed=embed)


    @staff()
    @commands.command(aliases=['rw'])
    async def removewarn(self, ctx:commands.Context, id:int, *,reason:str):
        document = await self.delete_infraction(id)
        if not document:
            return await ctx.send(f"Couldn't find the infraction with id: {id}")
        
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
        await ctx.send(f"Successfully deleted infraction with id **{id}**. More info about the infraction can be found in the logs.")

    async def removal_log(self, ctx, search):
        
        embed = discord.Embed(
            title = "Purge Command Used",
            colour = self.bot.colour,
            timestamp = datetime.utcnow()
        ).set_thumbnail(url=ctx.author.avatar_url)

        embed.set_footer(text=self.bot.footer)
        embed.add_field(name="Used By", value=ctx.author.mention)
        embed.add_field(name="Channel", value=ctx.channel.mention)
        embed.add_field(name="Messages Purged", value=search)

        await EmbedLog(ctx, embed).post_log()
        

    async def do_removal(self, ctx, limit, predicate):
        await ctx.message.delete()
        if limit > 2000:
            return await ctx.send(f'Too many messages to search given ({limit}/2000)')
        
        try:
            deleted = await ctx.channel.purge(limit=limit, check=predicate)
        except discord.Forbidden as e:
            return await ctx.send('I do not have permissions to delete messages.')
        except discord.HTTPException as e:
            return await ctx.send(f'Error: {e} (try a smaller search?)')

        spammers = Counter(m.author for m in deleted)
        deleted = len(deleted)
        messages = [f'{deleted} message{" was" if deleted == 1 else "s were"} removed.']
        if deleted:
            messages.append('')
            spammers = sorted(spammers.items(), key=lambda t: t[1], reverse=True)
            messages.extend(f'**{name}**: {count}' for name, count in spammers)

        to_send = '\n'.join(messages)

        if len(to_send) > 2000:
            await ctx.send(f'Successfully removed {deleted} messages.', delete_after=5)
        else:
            await ctx.send(to_send, delete_after=5)

        await self.removal_log(ctx, limit)
    


    @staff()
    @commands.group(invoke_without_command=True, aliases=['clear'])
    async def purge(self, ctx:commands.Context, search=1):
        """Deletes messages.
        
        Ignores pinned messages"""
        def pred(m):
            return not m.pinned
        await self.do_removal(ctx, search, pred)

    @staff()
    @purge.command()
    async def embeds(self, ctx:commands.Context, search=1):
        """Removes messages that have embeds in them."""
        await self.do_removal(ctx, search, lambda e: len(e.embeds))

    @staff()
    @purge.command()
    async def files(self, ctx:commands.Context, search=1):
        """Removes messages that have attachments in them."""
        await self.do_removal(ctx, search, lambda e: len(e.attachments))

    @staff()
    @purge.command()
    async def images(self, ctx:commands.Context, search=1):
        """Removes messages that have attachments and images in them."""
        await self.do_removal(ctx, search, lambda e: len(e.attachments) or len(e.embeds))

    @staff()
    @purge.command(aliases=['member'])
    async def user(self, ctx:commands.Context, member:discord.Member, search=1):
        """Removes messages by a certain user."""
        await self.do_removal(ctx, search, lambda e: e.author == member)

    @staff()
    @purge.command()
    async def contains(self, ctx:commands.Context, search=1,*, string:str):
        """Removes all messages containing a string/substring.

        The provided string should be atleast 3 characters long."""
        if len(string)>3:
            return await ctx.send("The provided string should be at least 3 characters long.")
        await self.do_removal(ctx, search, lambda e: string in e.content)


    @staff()
    @purge.command(name="bot")
    async def _bot(self, ctx:commands.Context, search=1, prefix=None):
        """Removes a bot user's messages and messages with their optional prefix"""

        def pred(msg):
            return (msg.webhook_id is None and msg.author.bot) or (prefix and msg.content.startswith(prefix))

        await self.do_removal(ctx, search, pred)

    @senior_staff()
    @commands.command()
    async def kick(self, ctx:commands.Context, offender:discord.Member, *,reason:str):
        """Kicks a user from the server."""
        await ctx.message.delete()
        if not self.hierarchy_check(ctx.author, offender):
            return await ctx.send("You cannot perform that action due to the hierarchy.")

        doc = await self.append_infraction(
            InfractionType.kick,
            offender,
            ctx.author,
            reason
        )


        embed = self.embed_builder(
            type= InfractionType.kick,
            title = InfractionType.kick.name,
            offender = offender,
            moderator = ctx.author,
            reason = reason,
            id = doc['id']
        )

        await EmbedLog(ctx, embed).post_log()

        user_embed = UserInfractionEmbed(InfractionType.kick, reason, doc['id']).embed()
        try:
            await offender.send(embed=user_embed)
        except:
            await ctx.send("Couldn't DM the user since their DMs are closed", delete_after=5.0)

        try:
            await ctx.send(f"Successfully kicked **{offender}**. Reason: *{reason}*")
            await offender.kick(reason=reason+f" Moderator: {ctx.author}")
        except Exception as e:
            await ctx.send(e)

    @senior_staff()
    @commands.command()
    async def ban(self, ctx:commands.Context, offender:Union[discord.Member, discord.User], *,reason:str):
        """Bans a user irrespective of them being in the server."""
        await ctx.message.delete()
        if not isinstance(offender, discord.User):
            if not self.hierarchy_check(ctx.author, offender):
                return await ctx.send("You cannot perform that action due to the hierarchy.")

        doc = await self.append_infraction(
            InfractionType.ban,
            offender,
            ctx.author,
            reason
        )


        embed = self.embed_builder(
            type= InfractionType.ban,
            title = InfractionType.ban.name,
            offender = offender,
            moderator = ctx.author,
            reason = reason,
            id = doc['id']
        )

        await EmbedLog(ctx, embed).post_log()

        user_embed = UserInfractionEmbed(InfractionType.ban, reason, doc['id']).embed()
        try:
            await offender.send(embed=user_embed)
        except:
            await ctx.send("Couldn't DM the user since their DMs are closed", delete_after=5.0)

        try:        
            await ctx.guild.ban(offender, reason=reason+f" Moderator: {ctx.author}", delete_message_days=7)
            await ctx.send(f"Banned **{offender}**.Reason: *{reason}*.")
        except Exception as e:
            await ctx.send(e)

    @senior_staff()
    @commands.command()
    async def unban(self, ctx:commands.Context, user:discord.User, *, reason:str):
        """Unbans a user from the server"""
        try:
            banned:discord.BanEntry = await ctx.guild.fetch_ban(user)
        except discord.NotFound:
            return await ctx.send("The given user is not banned.")
        except discord.HTTPException as e:
            return await ctx.send(e)
            
        

        doc = await self.append_infraction(
            InfractionType.unban,
            user,
            ctx.author,
            reason
        )

        await ctx.send(f"Succesfully unbanned **{banned.user}**.\nPreviously banned for: *{banned.reason}*.")

        embed = self.embed_builder(
            type= InfractionType.unban,
            title = InfractionType.unban.name,
            offender = user,
            moderator = ctx.author,
            reason = reason,
            id = doc['id']
        )

        await EmbedLog(ctx, embed).post_log()

        await ctx.guild.unban(user, reason=reason+f" Moderator: {ctx.author}")

    @staff()
    @commands.command()
    async def nick(self, ctx:commands.Context, user:discord.Member, *, nick:Optional[str]):
        """Changes the nickname of the user"""
        await ctx.message.delete()
        old = user.display_name
        if not self.hierarchy_check(ctx.author, user):
            return await ctx.send("You cannot perform that action due to the hierarchy.")
        try:
            await user.edit(nick = nick)
        except Exception as e:
            return await ctx.send(e)
        await ctx.send(f"Changed the nickname from *{old}* to **{user.display_name}**.", delete_after=5.0)

    @bot_channel()
    @commands.command()
    async def mywarns(self, ctx:commands.Context):
        container = []
        infs = self.mod_db.find({"offender":{"$eq":ctx.author.id}})
        async for inf in infs:
            if inf['type'] == int(InfractionType.unban):
                pass
            else:
                container.append(inf)

        if not container:
            return await ctx.send(f"You are squeaky clean. <:noice:811536531839516674> ")
        
        embed = await DMInfractionEmbed(ctx, container).embed_builder()
        await ctx.send(content="Sending you a list of your infractions.")
        return await ctx.author.send(embed=embed)


    @senior_staff()
    @commands.command(aliases=['cw','clearwarn'])
    async def clearwarns(self, ctx:commands.Context, user:Union[discord.User, discord.Member],*,reason:str):
        deleted = await self.mod_db.delete_many({"offender":{"$eq":user.id}})
        count = deleted.deleted_count
        if count:
            embed = discord.Embed(
                title="All Infractions Removed",
                timestamp = datetime.utcnow(),
                description = f"Removed {count} infractions from {user.mention}\n`({user} | {user.id})`",
                colour = 0x101010
            )
            embed.set_footer(text=self.bot.footer)
            embed.set_thumbnail(url=user.avatar_url)
            embed.add_field(name="Removed by", value=f"{ctx.author.mention} `({ctx.author.id})`")
            embed.add_field(name="Reason for Removal", value=reason, inline=False)

            await ctx.send(f"Deleted {count} infractions for **{user}**.")
            await EmbedLog(ctx, embed).post_log()
        else:
            await ctx.send("The user doesn't have any infraction registered.")


    @staff()
    @commands.command(name="bans")
    async def guild_bans(self, ctx:commands.Context):
        bans:list = await ctx.guild.bans()
        menu = menus.MenuPages(source=BanList(entries=bans, per_page=9))
        await menu.start(ctx)




    async def autowarn(self, offender:discord.Member, reason:str, message:discord.Message):
            
        doc = await self.append_infraction(
            InfractionType.autowarn,
            offender,
            self.bot.user,
            reason
        )

        embed = self.embed_builder(
            type = InfractionType.autowarn,
            title = InfractionType.autowarn.name,
            offender = offender,
            moderator = self.bot.user,
            reason = reason,
            id = doc['id']
        )

        await EmbedLog(await self.bot.get_context(message),embed).post_log()
        user_embed = UserInfractionEmbed(InfractionType.autowarn, reason, doc['id']).embed()
        try:
            await offender.send(embed=user_embed)
        except:
            pass

        await message.channel.send(f"Warned **{offender}**. Reason: *{reason}*", delete_after=5.0)



    # @commands.Cog.listener()
    # async def on_message(self, message:discord.Message):
    #     if not message.guild:
    #         return
    #     if not str(message.guild.id) in ("702180216533155933", "576325772629901312"):
    #         return
    #     elif message.author.bot:
    #         return
    #     elif await self.bot.is_owner(message.author):
    #         return
    #     elif STAFF in [role.id for role in message.author.roles] or COUNCIL in [role.id for role in message.author.roles]:
    #         return
    #     else:
    #         if not message.channel.id == 707177435912994877 or not str(message.channel.category_id) in ("680039943199784960", "706010454010363924"):
    #             invite_detected = UrlDetection().invite_check(message.content)
    #             if invite_detected:
    #                 await message.delete()
    #                 await self.autowarn(message.author, "Automatic action carried out for using an invite.", message)
               
    #         has_invalid_link = UrlDetection().convert(message.content)
    #         if not has_invalid_link:
    #             await message.delete()
    #             reason = "Automatic action carried out for using a blacklisted link."
            
    #             await self.autowarn(message.author, reason, message)
                



def setup(bot):
    bot.add_cog(Moderation(bot))