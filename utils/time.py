import humanize
import re

from datetime import datetime
from discord.ext import commands

def human_time(dt:datetime, **options) -> str:
    """Gives a nicely formated date object which is easy to read.
    Parameters
    ----------
    dt : datetime
        The datetime object we need to humanize.
    **options
        All valid arguments for `humanize.precisedelta`.
            minimum_unit: str   (default to seconds)
            suppress: tuple     (default to (), empty tuple)
            format: str         (default to %0.0f)
    Returns
    -------
    str
        The humanized datetime string.
    """
    minimum_unit = options.pop("minimum_unit", "seconds")
    suppress = options.pop("suppress", ())
    format = options.pop("format", "%0.0f")

    if dt is None:
        return 'N/A'
    return f"{humanize.precisedelta(datetime.utcnow() - dt, minimum_unit=minimum_unit, suppress=suppress, format=format)} ago"

# Credits to XuaTheGrate and Vexs for the time converted below.

time_regex = re.compile("(?:(\d{1,5})(h|s|m|d))+?")
time_dict = {"h":3600, "s":1, "m":60, "d":86400}

class TimeConverter(commands.Converter):
    async def convert(self, ctx, argument):
        args = argument.lower()
        matches = re.findall(time_regex, args)
        time = 0
        for v, k in matches:
            try:
                time += time_dict[k]*float(v)
            except KeyError:
                raise commands.BadArgument(f"{k} is an invalid time-key! h/m/s/d are valid!")
            except ValueError:
                raise commands.BadArgument(f"{v} is not a number!")
        return time
