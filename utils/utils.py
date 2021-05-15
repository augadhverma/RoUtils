from datetime import datetime
import enum
import time

class InfractionType(enum.Enum):
    autowarn = 0
    automute = 1
    warn = 2
    mute = 3
    kick = 4
    softban = 5
    ban = 6
    unban = 7

    def __str__(self) -> str:
        return self.name

    def __int__(self) -> int:
        return self.value

    def __repr__(self) -> str:
        return f"<InfractionType name='{self.name}' value={self.value}>"

class InfractionEntry:
    __slots__ = ('id', 'type', 'reason', 'mod_id', 'offender_id', 'time', 'until')

    def __init__(self, *, data:dict):
        self._update(data)

    def __int__(self) -> int:
        return self.id

    def __repr__(self) -> str:
        return f"<InfractionEntry id={self.id!r}> type={self.type!r} offender_id={self.offender_id!r} "\
               f"mod_id={self.mod_id!r} time={self.time!r} until={self.until!r}>"

    def __str__(self) -> str:
        return f"<@{self.offender_id}> was infracted by <@{self.mod_id}>.\n"\
               f"Type of infraction: {self.type.name}\n"\
               f"Reason: {self.reason}"

    def __eq__(self, o: object) -> bool:
        return isinstance(o, self) and o.id == self.id and o.time == self.time

    def __ne__(self, o: object) -> bool:
        return not self.__eq__(o)

    def _update(self, data:dict):
        self.type = InfractionType[data['type']]
        self.mod_id:int = data['moderator']
        self.offender_id:int = data['offender']
        self.time:time.time = data['time']
        self.until:time.time = data.get('until', None)
        self.reason:str = data['reason']
        self.id:int = data['id']

class TagEntry:
    __slots__ = ('id', 'name', 'content', 'created', 'aliases', 'uses', 'content', 'owner_id', 'raw')
    def __init__(self, *, data:dict) -> None:
        self._update(data)

    def __str__(self) -> str:
        return self.content

    def __repr__(self) -> str:
        return f"<TagEntry id='{self.id}' name='{self.name}' owner_id={self.owner_id} created={self.created} uses={self.uses}\n"\
               f"aliases='{len(self.aliases)} aliases'>"

    def __eq__(self, o: object) -> bool:
        return o.id == self.id

    def _update(self, data:dict):
        self.owner_id:int = data['owner']
        self.name:str = data['name']
        self.content:str = data['content']
        self.uses:int = data['uses']
        self.created:datetime = data['created']
        self.aliases:list = data.get('aliases', [])
        self.id:str = data['_id']
        self.raw = data

class TagNotFound(Exception):
    pass