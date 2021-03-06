from typing import Any
import aiohttp

class HTTPException(Exception):
    def __init__(self, status:int, reason:str, message:Any) -> None:
        self.status = status
        self.reason = reason
        self.message = message


async def get(*args, **kwargs) -> dict:
    async with aiohttp.ClientSession() as cs:
        async with cs.get(*args, **kwargs) as r:
            json_obj = await r.json()
            if r.status == 200:
                return json_obj
            else:
                raise HTTPException(r.status, r.reason, json_obj)