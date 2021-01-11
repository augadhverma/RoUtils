import discord
import datetime
import re

from discord.ext import commands


async def to_user(ctx:commands.Context, argument:str) -> discord.User:
    """Converts to a User

        The lookup strategy is as follows (in order):

            1. Lookup by ID.

            2. Lookup by mention.

            3. Lookup by name#discrim

            4. Lookup by name

    Args:
        ctx (commands.Context): The invocation context that the argument is being used in.
        argument (str): The argument that is being converted.

    Returns:
        discord.User: An instance of discord.User
    """
    return await commands.UserConverter().convert(ctx, argument)

async def to_member(ctx:commands.Context, argument:str) -> discord.Member:
    """Converts to a Member.

        All lookups are via the local guild. If in a DM context, then the lookup is done by the global cache.

        The lookup strategy is as follows (in order):

            1. Lookup by ID.

            2. Lookup by mention.

            3. Lookup by name#discrim

            4. Lookup by name

            5. Lookup by nickname

    Args:
        ctx (commands.Context): The invocation context that the argument is being used in.
        argument (str): The argument that is being converted.

    Returns:
        discord.Member: An instance of discord.Member
    """
    return await commands.MemberConverter().convert(ctx, argument)

time_regex = re.compile(r"(\d{1,5}(?:[.,]?\d{1,5})?)([smhd])")
time_dict = {"h":3600, "s":1, "m":60, "d":86400}

class TimeConverter(commands.Converter):
    async def convert(self, ctx, argument:str) -> datetime.datetime:
        matches = time_regex.findall(argument.lower())
        time = 0
        for v,k in matches:
            try:
                time+=time_dict[k]*float(v)
            except KeyError:
                raise commands.BadArgument("{} is an invalid time-key! h/m/s/d are valid!".format(k))
            except ValueError:
                raise commands.BadArgument("{} is not a number!".format(v))
        return time