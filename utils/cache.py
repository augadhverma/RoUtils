"""
A simple time cache.
Copyright (C) 2021  Augadh Verma

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

from __future__ import annotations

import time

from typing import (
    TypeVar,
    Any,
    Optional,
    Union,
    Iterator,
    Tuple,
    Mapping,
    Iterable
)

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
        __m: Union[Optional[Mapping[_KT, _VT]], Optional[Iterable[Tuple[_KT, _VT]]]] = None,
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
        self,  __m: Union[Optional[Mapping[_KT, _VT]], Optional[Iterable[Tuple[_KT, _VT]]]],
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
            if (time.monotonic() - item[0]) < self.__ttl:
                return item if self.show_time else item[1]
            else:
                self.__delitem__(k)
        raise KeyError()

    def __setitem__(self, k: _KT, v: _VT) -> None:
        return super().__setitem__(k, (time.monotonic() ,v))

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
            if (time.monotonic() - item[0]) < self.__ttl:
                to_return = True
            else:
                self.__delitem__(o)
        finally:
            self.show_time = original_time
            return to_return

    def __iter__(self) -> Iterator[_KT]:
        keys_to_del = []
        for k, v in self.items():
            if (time.monotonic() - v[0]) < self.__ttl:
                yield k
            else:
                keys_to_del.append(k)

        for k in keys_to_del:
            self.__delitem__(k)