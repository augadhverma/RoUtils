from discord.ext import commands


INTERN = 783068153856131072
STAFF = 652203841978236940
SENIORSTAFF = 693896132882989086
MANAGEMENT = 671634821323423754
COUNCIL = 626860276045840385

BOTCHANNEL = 678198477108543518

def admin():
    async def pred(ctx:commands.Context):
        if await ctx.bot.is_owner(ctx.author):
            return True
        try:
            roles = [r.id for r in ctx.author.roles]
        except AttributeError:
            return False
        else:
            if (MANAGEMENT in roles) or (COUNCIL in roles):
                return True
            else:
                return False
    return commands.check(pred)

def seniorstaff():
    async def pred(ctx:commands.Context):
        if await ctx.bot.is_owner(ctx.author):
            return True
        try:
            roles = [r.id for r in ctx.author.roles]
        except AttributeError:
            return False
        else:
            if (MANAGEMENT in roles) or (COUNCIL in roles) or (SENIORSTAFF in roles):
                return True
            else:
                return False
    return commands.check(pred)

def staff():
    async def pred(ctx:commands.Context):
        if await ctx.bot.is_owner(ctx.author):
            return True
        try:
            roles = [r.id for r in ctx.author.roles]
        except AttributeError:
            return False
        else:
            if (MANAGEMENT in roles) or (COUNCIL in roles) or (SENIORSTAFF in roles) or (STAFF in roles):
                return True
            else:
                return False
    return commands.check(pred)

def intern():
    async def pred(ctx:commands.Context):
        if await ctx.bot.is_owner(ctx.author):
            return True
        try:
            roles = [r.id for r in ctx.author.roles]
        except AttributeError:
            return False
        else:
            if (MANAGEMENT in roles) or (COUNCIL in roles) or (SENIORSTAFF in roles) or (STAFF in roles) or (INTERN in roles):
                return True
            else:
                return False
    return commands.check(pred)

def botchannel():
    async def pred(ctx:commands.Context):
        if ctx.guild is None:
            return True
        roles = [r.id for r in ctx.author.roles]
        if await ctx.bot.is_owner(ctx.author):
            return True
        elif (MANAGEMENT in roles) or (COUNCIL in roles) or (SENIORSTAFF in roles) or (STAFF in roles) or (INTERN in roles):
            return True
        elif ctx.channel.id == BOTCHANNEL:
            return True
        else:
            return False
    return commands.check(pred)
