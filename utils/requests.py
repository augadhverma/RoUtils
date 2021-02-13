import aiohttp

async def get(*args, **kwargs) -> dict:
    async with aiohttp.ClientSession() as cs:
        async with cs.get(*args, **kwargs) as r:
            return await r.json()