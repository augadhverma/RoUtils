"""
Custom lib for mongodb
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

from typing import Iterable, Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorCursor
from pymongo.results import (
    BulkWriteResult,
    DeleteResult,
    InsertManyResult,
    InsertOneResult,
    UpdateResult
)

class Client:
    def __init__(self, uri: str, db: str, collection: str = None, *, tz_aware = True, connect = True, **kwargs):
        """Forms a client connection with the MongoDB Database.

        Parameters
        ----------
        uri : str
            The URI or host used to log into the MongoDB database.
        db : str
            The name of the database to access.
        collection : str, optional
            The name of the collection to access, by default None
        tz_aware : bool, optional
            Makes the client connection timezone aware, by default True
        connect : bool, optional
            To reconnect to the Client connection automatically in the background, by default True
        """
        client = AsyncIOMotorClient(uri, tz_aware=tz_aware, connect=connect, **kwargs)
        db = client[db]
        self.db = db
        if collection:
            self._collection = db[collection]

    @property
    def collection(self) -> AsyncIOMotorCollection:
        """The collection currently accessing.

        Returns
        -------
        AsyncIOMotorCollection
            The collection currently accessing.
        """
        return self._collection

    @collection.setter
    def collection(self, name: str):
        self._collection = self.db[name]

    async def count_documents(self, filter: dict, **kwargs) -> int:
        return await self.collection.count_documents(filter, **kwargs)

    async def estimated_document_count(self, **kwargs) -> int:
        return await self.collection.estimated_document_count(**kwargs)

    async def insert_one(self, document: dict, **kwargs) -> InsertOneResult:
        return await self.collection.insert_one(document, **kwargs)

    async def insert_many(self, documents: Iterable[dict], ordered=True, **kwargs) -> InsertManyResult:
        return await self.collection.insert_many(documents, ordered=True, **kwargs)

    async def delete_one(self, filter: dict, **kwargs) -> DeleteResult:
        return await self.collection.delete_one(filter, **kwargs)

    async def delete_many(self, filter: dict, **kwargs) -> DeleteResult:
        return await self.collection.delete_many(filter, **kwargs)

    async def find_one(self, filter: dict, *args, **kwargs) -> Optional[dict]:
        return await self.collection.find_one(filter, *args, **kwargs)

    def find(self, filter: dict, *args, **kwargs) -> AsyncIOMotorCursor:
        return self.collection.find(filter, *args, **kwargs)

    async def update_one(self, filter: dict, update: dict, **kwargs) -> UpdateResult:
        return await self.collection.update_one(filter, update, **kwargs)

    async def update_many(self, filter: dict, update: dict, **kwargs) -> UpdateResult:
        return await self.collection.update_many(filter, update, **kwargs)
