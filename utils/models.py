"""
Somewhat useful models
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

import datetime
import time
import aiohttp
import discord

from typing import Any, Dict, Iterable, Iterator, List, Literal, Mapping, Optional, Tuple, TypeVar, Union
from enum import Enum
from discord.ext import commands
from discord.utils import MISSING
from bson import ObjectId

from aiohttp import ClientResponse
from requests import Response

_ResponseType = Union[ClientResponse, Response]

def format_dt(dt: datetime.datetime) -> str:
    return f"{discord.utils.format_dt(dt, 'F')} ({discord.utils.format_dt(dt, 'R')})"

def _flatten_error_dict(d: Dict[str, Any], key: str = '') -> Dict[str, str]:
    items: List[Tuple[str, str]] = []
    for k, v in d.items():
        new_key = key + '.' + k if key else k

        if isinstance(v, dict):
            try:
                _errors: List[Dict[str, Any]] = v['_errors']
            except KeyError:
                items.extend(_flatten_error_dict(v, new_key).items())
            else:
                items.append((new_key, ' '.join(x.get('message', '') for x in _errors)))
        else:
            items.append((new_key, v))

    return dict(items)

class HTTPException(Exception):
    def __init__(self, response: _ResponseType, message: Optional[Union[str, Dict[str, Any]]]):
        self.response: _ResponseType = response
        self.status: int = response.status  # type: ignore # This attribute is filled by the library even if using requests
        self.code: int
        self.text: str
        if isinstance(message, dict):
            self.code = message.get('code', 0)
            base = message.get('message', '')
            errors = message.get('errors')
            if errors:
                errors = _flatten_error_dict(errors)
                helpful = '\n'.join('In %s: %s' % t for t in errors.items())
                self.text = base + '\n' + helpful
            else:
                self.text = base
        else:
            self.text = message or ''
            self.code = 0

        fmt = '{0.status} {0.reason} (error code: {1})'
        if len(self.text):
            fmt += ': {2}'

        super().__init__(fmt.format(self.response, self.code, self.text))



class LogChannelNotFound(Exception):
    def __init__(self) -> None:
        pass

async def request(session: aiohttp.ClientSession, method: str, url: str, *args, **kwargs) -> dict:
    r = await session.request(method, url, *args, **kwargs)
    json = await r.json()
    if r.status == 200:
        return json
    else:
        raise HTTPException(r, json)

class InfractionColour(Enum):
    autowarn = discord.Colour.teal()
    automute = discord.Colour.teal()
    warn = discord.Colour.teal()
    mute = discord.Colour.orange()
    kick = discord.Colour.red()
    softban = discord.Colour.red()
    ban = discord.Colour.dark_red()
    unban = discord.Colour.green()
    autotimeout = discord.Colour.dark_orange()
    timeout = discord.Colour.dark_orange()

    def __str__(self) -> str:
        return self.name

    def __int__(self) -> int:
        return self.value

class InfractionType(Enum):
    autowarn = 0
    automute = 1
    warn = 2
    mute = 3
    kick = 4
    softban = 5
    ban = 6
    unban = 7
    autotimeout = 8
    timout = 9

    def __int__(self) -> int:
        return self.value

    def __str__(self) -> str:
        return self.name

class Infraction:
    def __init__(self, document: dict) -> None:
        self._document: dict = document
        self._id: ObjectId = ObjectId(document['_id'])
        self.id: int = document['id']
        self.moderator: int = document['moderator']
        self.offender: int = document['offender']
        self.deleted: bool = document.get('deleted', False)
        self.reason: str = document['reason']
        self.type: InfractionType = InfractionType(document['type'])
        self.created: datetime.datetime = self._id.generation_time
        self.until: Optional[float] = document.get('until')
        if isinstance(self.until, float):
            self.until: datetime.datetime = datetime.datetime.utcfromtimestamp(self.until)
        self.colour: InfractionColour = InfractionColour[self.type.name]
        self.guild_id: int = document['guild_id']


    @property
    def case(self) -> str:
        return f"Case #{self.id} | {self.type.name.capitalize()}"

    def embed_description(self, option: Literal['offender', 'channel', 'log']) -> str:
        if option == "offender":
            description = f"**Reason:** {self.reason}"
        elif option == "channel":
            description = f"<@{self.offender}> (`{self.offender}`) was infracted | **{self.type.name}**"
        elif option == "log":
            description = (
                f"**Offender:** <@{self.offender}> (`{self.offender}`)\n"
                f"**Moderator:** <@{self.moderator}> (`{self.offender}`)\n"
                f"**Reason:** {self.reason}"

            )

        return description

    def embed(self, option: Literal['offender', 'channel', 'log']) -> discord.Embed:
        embed = Embed(
            colour=self.colour.value,
            timestamp=self.created,
            title=self.case,
            description=self.embed_description(option)
        )

        embed.set_footer(text="Infraction issued at")

        if self.until and option != 'channel':
            embed.add_field(name="Valid Until", value=discord.utils.format_dt(self.until, "F"))

        return embed

_KT = TypeVar('_KT')
_VT = TypeVar('_VT')

def lower_object(o: Any) -> Any:
    if isinstance(o, str):
        return o.casefold()
    return o

class CaseInsensitiveDict(dict):
    """
    A caseinsensitive dictionary. I have implemented the use of `casefold` since it is more stronger and aggressive.

    Can be initialised in the same ways as a normal dictionary:

    Examples
    ---------

    CaseInsensitiveDict() -> Creates a new empty dictionary

    CaseInsensitiveDict(one=1, two=2) -> Generates a dictionary {"one":1, "two":2}

    CaseInsensitiveDict([("one", 1),("two", 2)]) -> Generates a dictionary {"one":1, "two":2}

    Limitations
    ------------
    If two keys in 'lower' are same, then the value of latter will be used, i.e. if we have a dict `{'a':1, 'A':2}`
    this will then become `{'a':2}`. This happens due to converting the keys to lowercase.
    """
    def __init__(
        self,
        __m: Optional[Union[Optional[Mapping[_KT, _VT]], Optional[Iterable[Tuple[_KT, _VT]]]]] = None,
        **kwargs
    ) -> None:
        super().__init__(self.__create_dict(__m, kwargs))
    def __create_dict(self, __m, kwargs) -> dict:
        if __m:
            temp = dict(__m)
        elif kwargs:
            temp = dict(kwargs)
        else:
            return {}
        new = {}
        for k, v in temp.items():
            new[lower_object(k)] = v
        return new

    def __getitem__(self, k: _KT) -> _VT:
        return super().__getitem__(lower_object(k))

    def __setitem__(self, k: _KT, v: _VT) -> None:
        return super().__setitem__(lower_object(k), v)

    def __delitem__(self, v: _KT) -> None:
        return super().__delitem__(lower_object(v))

    def __contains__(self, o: object) -> bool:
        return super().__contains__(lower_object(o))

    def __iter__(self) -> Iterator[_KT]:
        return super().__iter__()

    def get(self, key: _KT, default=None):
        return super().get(lower_object(key), default)

    def pop(self, key: _KT, default=None):
        return super().pop(lower_object(key), default)

    def popitem(self) -> Tuple[_KT, _VT]:
        return super().popitem()

    def update(
        self,
        __m: Union[Optional[Mapping[_KT, _VT]], Optional[Iterable[Tuple[_KT, _VT]]]] = None,
        **kwargs: _VT
    ) -> None:
        if __m:
            temp = dict(__m)
        elif kwargs:
            temp = dict(kwargs)
        else:
            return

        for k, v in temp.items():
            self[lower_object(k)] = v

class Cache(CaseInsensitiveDict):
    def __init__(
        self,  __m: Union[Optional[Mapping[_KT, _VT]], Optional[Iterable[Tuple[_KT, _VT]]]] = {},
        *,
        seconds:int = 10800,
        show_time: bool = False,
        **kwargs
    ) -> None:
        self.__ttl = seconds
        self.show_time = show_time
        super().__init__(__m=__m, **kwargs)

    def __getitem__(self, k: _KT) -> _VT:
        item = self.get(k)
        if item:
            if (time.monotonic() - item[1]) < self.__ttl:
                return item if self.show_time else item[0]
            else:
                self.__delitem__(k)
        raise KeyError()

    def __setitem__(self, k: _KT, v: _VT) -> None:
        return super().__setitem__(k, (v, time.monotonic()))

    def __contains__(self, o: object) -> bool:
        if o not in self.keys():
            return False
        original_time = self.show_time
        self.show_time = True
        
        to_return = False
        
        try:
            item = self.__getitem__(o)
        except KeyError:
            to_return = False
        else:
            if (time.monotonic() - item[1]) < self.__ttl:
                to_return = True
            else:
                self.__delitem__(o)
        finally:
            self.show_time = original_time
            return to_return

    def __iter__(self) -> Iterator[_KT]:
        keys_to_del = []
        for k, v in self.items():
            if (time.monotonic() - v[1]) < self.__ttl:
                yield k
            else:
                keys_to_del.append(k)

        for k in keys_to_del:
            self.__delitem__(k)

class Embed(discord.Embed):
    def __init__(self, *, bot=None, footer: str = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.colour = kwargs.get('colour', bot.colour if bot else discord.Colour.blue())
        self.set_footer(text=footer or bot.footer if bot else '\uFEFF')
        self.timestamp = kwargs.get('timestamp', discord.utils.utcnow())

"""

  _id: Mongo Object,
  name: string,
  uses: integer,
  embed: Object[colour: integer, url: string, image: string, thumbnail: string, fields: Array[name=string, value=string, inline=boolean], Array[...]],
  owner: integer,
  button_urls: Array[Array[label=string, url=string, emoji="string"], Array[...]],
  guild: integer


"""

URL = TypeVar('URL', str, bytes)

class TagEmbed:
    def __init__(self, doc: dict):
        self.title: str = doc.get('title', None)
        self.description: str = doc.get('description', None)
        self.colour: int | discord.Colour = doc.get('colour', discord.Colour.blue())
        self.url: Optional[URL] = doc.get('url', None)
        self.image: Optional[URL] = doc.get('image', None)
        self.thumbnail: Optional[URL] = doc.get('thumbnail', None)
        self.fields: list = doc.get('fields', [])

class TagEntry:
    def __init__(self, document: dict) -> None:
        self._id: ObjectId = document['_id']
        self.name: str = document['name']
        self._uses: int = document['uses']
        self._content: str | None = document.get('content', None)
        
        self.embed: TagEmbed = TagEmbed(document.get('embed', dict()))
        # {colour:int, url:str, image:string, thumbnail:string, fields: [["name", "value", inline], ...]}

        self.enable_embed: bool = document.get('enable_embed', False)
        self.owner: int = document['owner']
        self.guild: int = document.get('guild', 0)
        self._button_urls: list[list[str]] = document.get('button_urls', []) # [["label","url"], ...]

    @property
    def content(self) -> str | None:
        if self._content:
            return self._content.replace("\\n", "\n")
        return None

    @content.setter
    def content(self, value: str | None) -> None:
        self._content = value

    @property
    def uses(self) -> int:
        return self._uses

    @uses.setter
    def uses(self, value:int) -> None:
        self.uses = value

    def send_values(self) -> dict[str, Any]:
        to_return = {
            "content":self.content,
            "embed":MISSING,
            "view":MISSING
        }
        if self.enable_embed:
            embed = discord.Embed(
                title=self.embed.title,
                description=self.embed.description,
                colour=self.embed.colour,
                timestamp=discord.utils.utcnow(),
                url=self.embed.url
            )

            embed.set_image(url=self.embed.image)
            embed.set_thumbnail(url=self.embed.thumbnail)

            if self.embed.fields:
                for field in self.embed.fields:
                    embed.add_field(name=field[0], value=field[1], inline=field[2])
            to_return['embed'] = embed

        if self._button_urls:
            view = discord.ui.View()

            for button_list in self._button_urls:
                button_list: list[str]
                
                button = discord.ui.Button(
                    style=discord.ButtonStyle.link,
                    label=button_list[0],
                    url=button_list[1],
                )

                view.add_item(button)
            
            to_return['view'] = view

        return to_return

class GuildSettings:
    def __init__(self, document: dict) -> None:
        self._document: dict = document
        self.id: int = document['_id'] #guild id
        self.prefix: str = document['prefix']
        self.log_channels: dict[str, int | None] = document['logChannels']
        self.extra_roles: dict[str, int | None] = document['extraRoles']
        self.mod_roles: dict[str, int | None] = document['modRoles']
        self.command_disabled_channels: list[int] = document['commandDisabledChannels']
        self.bad_words: list[str] = document['badWords']
        self.domains_whitelisted: list[str] = document['domainsWhitelisted']
        self.detection_exclusive_channels: list[int] = document['detectionExclusiveChannels']
        self.mute_role: int | None = document.get('muteRole', None)
        self.domain_detection: bool = document['domainDetection']
        self.bad_word_detection: bool = document['badWordDetection']
        self.timeout_instead_of_mute: bool = document['timeoutInsteadOfMute']
        self.tickets_channel: int | None = document.get('ticketsChannel')
        self.suppress_warns: List[int] = document.get('suppressWarns', [])

class CustomEmbeds:
    def __init__(self, document: dict) -> None:
        self._document = document
        self._id: ObjectId = ObjectId(document['_id'])
        self.id: int = document['id']
        self.embed_data: dict = document['embedData']
        self.embed: discord.Embed = discord.Embed().from_dict(self.embed_data)