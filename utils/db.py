from typing import Iterable, Union
from motor import motor_asyncio as ma

from pymongo.results import DeleteResult, InsertManyResult, InsertOneResult, UpdateResult



pwd = "HasAccessToAllDatabases"

class Connection:
    def __init__(self, db, collection) -> None:
        client = ma.AsyncIOMotorClient(f"mongodb+srv://Admin:{pwd}@cluster0.ulwxb.mongodb.net/{db}?retryWrites=true&w=majority")
        self.db = client[db]
        self.collection = self.db[collection]

    async def insert_one(self, document:dict) -> InsertOneResult:
        return await self.collection.insert_one(document)

    async def insert_many(self, documents:Iterable) -> InsertManyResult:
        return await self.collection.insert_many(documents)

    async def find_one(self, filter:dict) -> Union[dict, None]:
        return await self.collection.find_one(filter)

    def find(self, filter) -> ma.AsyncIOMotorCursor:
        return self.collection.find(filter)

    async def update_one(self, filter:dict, update:dict) -> UpdateResult:
        return await self.collection.update_one(filter, update)

    async def update_many(self, filter:dict, update:dict) -> UpdateResult:
        return await self.collection.update_many(filter, update)

    async def delete_one(self, filter:dict) -> DeleteResult:
        return await self.collection.delete_one(filter)

    async def delete_many(self, filter:dict) -> DeleteResult:
        return await self.collection.delete_many(filter)

    async def count_documents(self, filter:dict, *args, **kwargs) -> int:
        return await self.collection.count_documents(filter, *args, **kwargs)