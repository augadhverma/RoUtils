import humanize
from datetime import datetime

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