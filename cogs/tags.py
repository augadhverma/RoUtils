"""
The tag module.
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

from typing import Literal, Optional
import discord

from discord import app_commands
from discord.ext import commands
from difflib import get_close_matches
from utils import Bot, TagEntry, Embed, SimplePages, Context, check_perms, is_bot_channel, has_setting_role, TagNotFound

OWNER_ERROR_MESSAGE = 'You cannot do this action since you do not own this tag.'

class TagPageEntry:
    __slots__ = ('name',)

    def __init__(self, entry: TagEntry):
        self.name = entry.name

    def __str__(self) -> str:
        return f'{self.name}'

class TagPages(SimplePages):
    def __init__(self, entries: list[TagEntry], *, interaction: discord.Interaction, bot: Bot, per_page: int = 12, **kwargs) -> None:
        converted = [TagPageEntry(entry) for entry in entries]
        super().__init__(converted, per_page=per_page, interaction=interaction, bot=bot, **kwargs)

class Revert(discord.ui.View):
    def __init__(self, invoker_id: int, timeout : float | None = 180):
        super().__init__(timeout=timeout)
        self.value = False
        self.invoker_id = invoker_id

    @discord.ui.button(label="Revert Back?", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.invoker_id:
            return await interaction.response.send_message(OWNER_ERROR_MESSAGE, ephemeral=True)
        else:
            self.value = True
            button.style = discord.ButtonStyle.success
            button.disabled = True
            button.label = "Successfully Reverted Back."
            await interaction.response.edit_message(view=self)
            self.stop()

@app_commands.guild_only()
class Tags(commands.GroupCog, name="tag"):
    def __init__(self, bot: Bot):
        self.bot = bot
        super().__init__()

    async def get_tag(self, name: str, *, guild: int = None, update_uses: bool = False) -> TagEntry:
        
        query = {"name":{"$eq":name}, "guild":{"$eq":guild}}
        search_query = {"guild":{"$eq":guild}}
            
        document = await self.bot.tags.find_one(query)

        if document is None:
            searches = []
            async for tag in self.bot.tags.find(search_query):
                searches.append(tag['name'])

            matches = get_close_matches(name, searches)
            if matches:
                raise TagNotFound("Tag not found. Did you mean...\n"+"\n".join(m for m in matches))
            else:
                raise TagNotFound("Tag not found.")

        tag = TagEntry(document=document)

        if update_uses:
            uses = tag.uses
            uses += 1
            await self.bot.tags.update_one({'_id':tag._id}, {'$set':{'uses':uses}})

        return tag

    @app_commands.command(name="view", description="Displays the output of a previously set tag.")
    @app_commands.describe(name="Name of the tag.")
    @is_bot_channel()
    async def tag_view(self, interaction: discord.Interaction, name: str) -> None:
        
        tag = await self.get_tag(name=name, guild=interaction.guild_id, update_uses=True)
        
        values = tag.send_values()

        content = values['content']
        embed = values['embed']
        view = values['view']
        await interaction.response.send_message(content=content, embed=embed, view=view)

    @app_commands.command(name="create", description="Creates a new tag.")
    @app_commands.describe(
        name="Name of the tag to be created.",
        content="Content of the tag to send.",
        enable_embed="Whether to enable embed to be sent or not."
    )
    @is_bot_channel()
    async def create(
        self,
        interaction: discord.Interaction,
        name: str,
        content: Optional[str],
        enable_embed: Optional[Literal['Yes', 'No']]
    ) -> None:
        try:
            await self.get_tag(name=name, guild=interaction.guild_id)    
            return await interaction.response.send_message(f"Tag `{name}` already exists.", ephemeral=True)
        except TagNotFound:
            pass
        
        document = {
            "name":name,
            "content":content,
            "uses":0,
            "guild":interaction.guild.id,
            "owner":interaction.user.id,
            "embed":{},
            "button_urls":[],
            "enable_embed":True if enable_embed == 'Yes' else False
        }

        insert = await self.bot.tags.insert_one(document)
        await interaction.response.send_message(
            f"Tag with name `{name}` successfully created.\nHere is a specific id: `{insert.inserted_id}`. It is useless btw ;)"
        )

    edit = app_commands.Group(name='edit', description="To edit verious components of tags.")

    @edit.command(name="embed", description="Edit the embed output for the tag if any.")
    @app_commands.describe(
        name="Name of the tag.",
        title="Title of the embed.",
        description="Description of the embed.",
        url="The URL in the title.",
        image="URL of the image to add to the embed.",
        thumbnail="URL of the thumbnail to add to the embed.",
        enable_embed="Whether to show the embed output or not."
    )
    @is_bot_channel()
    async def edit_embed(
        self,
        interaction: discord.Interaction,
        name: str,
        title: Optional[str],
        description: Optional[str],
        url: Optional[str],
        image: Optional[str],
        thumbnail: Optional[str],
        enable_embed: Optional[Literal['Yes', 'No']]
    ) -> None:
        tag = await self.get_tag(name=name, guild=interaction.guild_id)
            
        if tag.owner != interaction.user.id:
            return await interaction.response.send_message(OWNER_ERROR_MESSAGE, ephemeral=True)

        colour = int(discord.Colour.blue())

        if enable_embed == 'Yes':
            enable = True
        elif enable_embed == 'No':
            enable = False
        else:
            enable = tag.enable_embed

        if title == 'N/A':
            title = None
        elif title is None:
            title = tag.embed.title
        
        if description == 'N/A':
            description = None
        elif description is None:
            description = tag.embed.description

        if url == 'N/A':
            url = None
        elif url is None:
            url = tag.embed.url

        if image == 'N/A':
            image = None
        elif image is None:
            image = tag.embed.image

        if thumbnail == 'N/A':
            thumbnail = None
        elif thumbnail is None:
            thumbnail = tag.embed.thumbnail

        embed_doc = {
            "title":title,
            "description":description,
            "colour":colour,
            "url":url,
            "image":image,
            "thumbnail":thumbnail,
            "fields":tag.embed.fields
        }

        await self.bot.tags.update_one({'_id':tag._id}, {'$set':{'embed':embed_doc}})
        await self.bot.tags.update_one({'_id':tag._id}, {'$set':{'enable_embed':enable}})

        note = "Enable embed for the tag to see the embed in the output." 
        return await interaction.response.send_message(f"Tag embed successfully updated. {note if not enable else ''}")

    @edit.command(name="content", description="Edit the normal message of the tag.")
    @app_commands.describe(name="The name of the tag.", content="The new content.")
    @is_bot_channel()
    async def edit_content(self, interaction: discord.Interaction, name: str, content: str) -> None:
        tag = await self.get_tag(name=name, guild=interaction.guild_id)
            
        if tag.owner != interaction.user.id:
            return await interaction.response.send_message(OWNER_ERROR_MESSAGE, ephemeral=True)

        if content == 'N/A':
            content = None

        await self.bot.tags.update_one({'_id':tag._id}, {'$set':{'content':content}})
        await interaction.response.send_message("Tag content successfully updated.")

    @edit.command(name="buttons", description="Add/Remove Link Button from the tag.")
    @app_commands.describe(
        name="The name of the tag.",
        option="Whether to add or remove a button.",
        label="The label of the button.",
        url="The URL this button points to. (Must be HTTP/HTTPS)."
    )
    async def edit_buttons(
        self,
        interaction: discord.Interaction,
        name: str,
        option: Literal['Add', 'Remove'],
        label: str,
        url: Optional[str]
    ) -> None:
        tag = await self.get_tag(name, guild=interaction.guild_id)

        if tag.owner != interaction.user.id:
            return await interaction.response.send_message(OWNER_ERROR_MESSAGE, ephemeral=True)

        if option == 'Remove':
            for buttons in tag._button_urls:
                try:
                    if buttons[0] == label:
                        try:
                            tag._button_urls.remove(buttons)
                            break
                        except ValueError:
                            pass                        
                except IndexError:
                    pass
            
            description = f"Successfully removed button ({label} → {buttons[1]})."
                
        elif option == 'Add':
            if url is None:
                return await interaction.response.send_message("Please provide a url.", ephemeral=True)
            
            button = [label, url]
            tag._button_urls.append(button)
            description = f"Successfully added button ({label} → {url})."

        await self.bot.tags.update_one({'_id':tag._id}, {'$set':{'button_urls':tag._button_urls}})

        embed = Embed(
            title="Success",
            colour=discord.Colour.green(),
            description=description
        )

        await interaction.response.send_message(embed=embed)        
            

    @app_commands.command(name="info", description="Shows information about the tag.")
    @app_commands.describe(name="The name of the tag.")
    async def info(self, interaction: discord.Interaction, name: str) -> None:
        tag = await self.get_tag(name=name, guild=interaction.guild_id)
        
        embed = Embed(
            bot=self.bot,
            title=name,
            timestamp=tag._id.generation_time
        )

        embed.set_footer(text="Tag created at")

        user = self.bot.get_user(tag.owner)
        if user is None:
            try:
                user = await self.bot.fetch_user(tag.owner)
            except (discord.NotFound, discord.HTTPException):
                user = None
            except Exception as e:
                raise e
        
        if user is not None:
            embed.set_author(name=str(user), icon_url=user.display_avatar.url)
        
        embed.add_field(name="Owner", value=user.mention if user else f"<@{tag.owner}>")
        embed.add_field(name="Uses", value=f"{tag.uses}")
        embed.add_field(name="Embed Enabled", value="Yes" if tag.enable_embed else "No")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="transfer", description="Transfers the ownership of a tag.")
    @app_commands.describe(name="The name of the tag to transfer.", user="The user to tranfer the ownership of tag.")
    @is_bot_channel()
    async def transfer(self, interaction: discord.Interaction, name: str, user: discord.Member) -> None:
        tag = await self.get_tag(name=name, guild=interaction.guild_id)
            
        if tag.owner != interaction.user.id:
            return await interaction.response.send_message(OWNER_ERROR_MESSAGE, ephemeral=True)

        await self.bot.tags.update_one({'_id':tag._id}, {'$set':{'owner':user.id}})

        embed = Embed(
            bot=self.bot,
            title="Success!",
            description=f"Tag successfully transferred to {user.mention}",
            colour=discord.Colour.green()
        )

        view = Revert(interaction.user.id)

        await interaction.response.send_message(embed=embed, view=view)

        await view.wait()
        if view.value:
            await self.bot.tags.update_one({'_id':tag._id}, {'$set':{'owner':tag.owner}})

            embed.title = "Successfully Reverted Back!"
            embed.description = f"Tag successfully transferred back to {interaction.user.mention}"

            await interaction.edit_original_message(embed=embed, view=view)

    @app_commands.command(name="delete", description="Deletes a tag. Server administrator can delete any tag.")
    @app_commands.describe(name="The name of the tag.")
    @is_bot_channel()
    async def delete(self, interaction: discord.Interaction, name: str) -> None:
        tag = await self.get_tag(name=name, guild=interaction.guild_id)
            
        check = (
            tag.owner != interaction.user.id
            and not interaction.user.guild_permissions.administrator
        )

        if check:
            return await interaction.response.send_message(OWNER_ERROR_MESSAGE, ephemeral=True)

        view = Revert(interaction.user.id, 30)

        embed = Embed(
            bot=self.bot,
            title="Success!",
            description="Tag successfully deleted",
            colour=discord.Colour.green()
        )

        await interaction.response.send_message(embed=embed, view=view)

        await view.wait()
        if view.value:
            embed.title = "Reverted back!"
            embed.description = "The tag was restored from the bin \N{WASTEBASKET}!"
            await interaction.edit_original_message(embed=embed)
        else:
            await self.bot.tags.delete_one({'_id':tag._id})
        
        
    @app_commands.command(name='all', description="Shows all the tags for the current server.")
    @is_bot_channel()
    async def tag_all(self, interaction: discord.Interaction) -> None:
        tags = []
        async for t in self.bot.tags.find({'guild':interaction.guild_id}):
            tags.append(TagEntry(t))

        if tags:
            embed = Embed(
                bot=self.bot,
                title="Server Tags"
            )
            pages = TagPages(entries=tags, interaction=interaction, bot=self.bot, embed=embed)
            await pages.start()
        else:
            await interaction.response.send_message('This server has no tags.')
        

    @app_commands.command(name="search", description="Searches for a tag.")
    @app_commands.describe(name="The tag name to search for.")
    @is_bot_channel()
    async def tag_search(self, interaction: discord.Interaction, name: str) -> None:
        tags: list[TagEntry] = []
        async for t in self.bot.tags.find({"guild":interaction.guild_id}):
            tags.append(TagEntry(t))

        matches = get_close_matches(name, [t.name for t in tags], n=int(len(tags)//1.5), cutoff=0.45)

        if matches:
            possibilities = []
            for t in tags:
                if t.name in matches:
                    possibilities.append(t)

            pages = TagPages(entries=possibilities, interaction=interaction, bot=self.bot)
            await pages.start()
        else:
            await interaction.response.send_message("Could not find a tag with that name")

    @app_commands.command(name="list", description="Shows tags made by a user.")
    @app_commands.describe(user="The user whose tags you want to see.")
    @is_bot_channel()
    async def tag_list(self, interaction: discord.Interaction, user: discord.Member) -> None:
        tags = []
        async for t in self.bot.tags.find({'guild':interaction.guild_id, "owner":user.id}):
            tags.append(TagEntry(t))

        if tags:
            embed = Embed(
                bot=self.bot,
                title=f"All tags by {user}"
            )
            pages = TagPages(entries=tags, interaction=interaction, bot=self.bot, embed=embed)
            await pages.start()
        else:
            await interaction.response.send_message(f"{user} has not made any tags.")

    
    @commands.Cog.listener("on_message")
    async def message_tags(self, message: discord.Message) -> None:
        if message.guild is None:
            return
        if message.author.bot:
            return

        ctx = await self.bot.get_context(message, cls=Context)
        if ctx.valid:
            return
        if ctx.prefix and message.content.startswith(ctx.prefix):
            _, name = message.content.split(ctx.prefix, maxsplit=1)
        else:
            return

        settings = await self.bot.get_guild_settings(message.guild.id)

        checks = (
            await check_perms(ctx, {'manage_messages':True}) or
            await has_setting_role(ctx, 'admin')
        )

        if not checks:
            if ctx.channel.id in settings.command_disabled_channels:
                return
        try:
            tag = await self.get_tag(name, guild=ctx.guild.id, update_uses=True)
        except TagNotFound:
            return        
        
        values = tag.send_values()

        content = values['content']
        embed = values['embed']
        view = values['view']
    
        await ctx.send(content=content, embed=embed, view=view, reference=ctx.replied_reference, allowed_mentions=discord.AllowedMentions(replied_user=True))

async def setup(bot: Bot):
    await bot.add_cog(Tags(bot))