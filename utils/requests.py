import aiohttp

async def get(*args, **kwargs) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(*args, **kwargs) as r:
            return await r.json()