from discord.ext import commands

STAFF = 652203841978236940
SENIORSTAFF = 693896132882989086
MANAGEMENT = 671634821323423754
COUNCIL = 626860276045840385
BOTCHANNEL = 678198477108543518


def council():
    async def pred(ctx:commands.Context):
        if await ctx.bot.is_owner(ctx.author):
            return True
        elif MANAGEMENT in [role.id for role in ctx.author.roles] or COUNCIL in [role.id for role in ctx.author.roles]:
            return True
        else:
            return False
    return commands.check(pred)

def senior_staff():
    def pred(ctx:commands.Context):
        if council():
            return True
        elif SENIORSTAFF in [role.id for role in ctx.author.roles]:
            return True
        else:
            return False
    return commands.check(pred)

def staff():
    def pred(ctx:commands.Context):
        if senior_staff():
            return True
        elif STAFF in [role.id for role in ctx.author.roles]:
            return True
        else:
            return False
    return commands.check(pred)

def bot_channel():
    def pred(ctx:commands.Context):
        if staff():
            return True
        elif ctx.guild is None:
            return True
        elif ctx.channel.id == BOTCHANNEL:
            return True
        else:
            return False
    return commands.check(pred)