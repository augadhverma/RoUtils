"""
Holds Roblox Models.
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

import datetime

from utils import CaseInsensitiveDict

def roblox_time(time: str) -> datetime.datetime:
    return datetime.datetime.strptime(time, '%Y-%m-%dT%H:%M:%S.%fZ')

def time_roblox(time: datetime.datetime = None) -> str:
    time = time or datetime.datetime.now(datetime.timezone.utc)
    return datetime.datetime.strftime(time, '%Y-%m-%dT%H:%M:%S.%fZ')

class BaseUser:
    name: str
    id: int
    display_name: str
    profile_url: str
    avatar_url: str

    __slots__ = ('name', 'id', 'display_name', 'profile_url', 'avatar_url')

    def __init__(self, data: dict) -> None:
        self._update(CaseInsensitiveDict(data))

    def __int__(self) -> int:
        return self.id

    def __str__(self) -> str:
        return self.name

    def _update(self, data: CaseInsensitiveDict):
        if not isinstance(data, CaseInsensitiveDict):
            data = CaseInsensitiveDict(data)

        self.name = data['name']
        self.id = data['id']
        self.display_name = data['displayname']
        self.profile_url = f'https://www.roblox.com/users/{self.id}/profile'
        self.avatar_url = f'https://www.roblox.com/Thumbs/Avatar.ashx?x=720&y=720&Format=Png&userId={self.id}'

class User(BaseUser):

    __slots__ = BaseUser.__slots__ + ('description', 'created_at', 'is_banned')

    description: str
    created_at: datetime.datetime
    is_banned: bool

    def __init__(self, data: dict):
        super().__init__(data)

    def __eq__(self, o: object) -> bool:
        return isinstance(o, BaseUser) and o.id == self.id

    def __ne__(self, o: object) -> bool:
        return not self.__eq__(o)

    def _update(self, data: CaseInsensitiveDict):
        super()._update(data)

        self.description = data.get('description', '')
        self.created_at = roblox_time(data['created'])
        self.is_banned = data.get('isBanned', False)

class Role:

    __slots__ = ('name', 'id', 'membercount', 'rank')

    name: str
    id: int
    rank: int
    membercount: int

    def __init__(self, data: dict):
        self._update(CaseInsensitiveDict(dict))

    def __str__(self) -> str:
        return self.name

    def __int__(self) -> int:
        return self.id

    def __eq__(self, o: object) -> bool:
        return isinstance(o, self.__class__) and o.id == self.id

    def __ne__(self, o: object) -> bool:
        return not self.__eq__(o)

    def _update(self, data: CaseInsensitiveDict):
        self.id = data['id']
        self.name = data['name']
        self.rank = data['rank']
        self.membercount = data.get('membercount', 0)

class Member(BaseUser):
    __slots__ = BaseUser.__slots__ + ('role', 'group_id')

    role: Role
    group_id: int

    def __init__(self, data: dict, group_id: int) -> None:
        super()._update(CaseInsensitiveDict(data))
        self.group_id = group_id

    def __eq__(self, o: object) -> bool:
        return isinstance(o, BaseUser) and o.id == self.id

    def __ne__(self, o: object) -> bool:
        return self.__eq__(o)

    def _update(self, data: CaseInsensitiveDict):
        super()._update(CaseInsensitiveDict(data))

        self.role = Role(data['role'])