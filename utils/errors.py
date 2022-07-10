import discord
from discord.app_commands import AppCommandError

class ReasonError(AppCommandError):
    pass

class CannotUseBotCommand(AppCommandError):
    def __init__(self, channel: discord.TextChannel, message: str | None = None) -> None:
        super().__init__(message or f'App Commands are disabled in #{channel}.')

class TagNotFound(discord.DiscordException):
    pass