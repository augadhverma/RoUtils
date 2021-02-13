import enum

class CacheType(enum.Enum):
    RobloxUser = "robloxUser"


class Cache:
    def __init__(self) -> None:
        self.cache = {
            "robloxUser":{}
        }

    def get(self, cache_type:CacheType, item_id:str):
        if item_id in self.cache[cache_type.value]:
            return self.cache[cache_type.value][item_id]

        else:
            return False

    def set(self, cache_type:CacheType, item_id:str, item_obj):
        self.cache[cache_type.value][item_id] = item_obj