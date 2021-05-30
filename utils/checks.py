from discord.ext import commands

class NotBotChannel(Exception):
    pass

class NotStaff(Exception):
    pass

class NotAdmin(Exception):
    pass

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
                raise NotAdmin(f"{ctx.author} is not an admin.")
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
                raise NotStaff(f"{ctx.author} is not a senior staff member.")
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
                raise NotStaff(f"{ctx.author} is not a staff member.")
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
                raise NotStaff(f"{ctx.author} is not a staff member.")
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
            raise NotBotChannel(f"`{ctx.command.name}` can be only used in the bot commands channel.")
    return commands.check(pred)
