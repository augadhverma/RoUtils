import motor
import os

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCursor

from pymongo.results import InsertOneResult, UpdateResult, DeleteResult

class Mod:
    def __init__(self, collection):
        modClient = AsyncIOMotorClient(os.environ.get("ModClient"))
        db = modClient['Moderation']
        self.collection:AsyncIOMotorClient = db[collection]

    @property
    async def count(self) -> int:
        """Returns the count of inserted documents

        Returns:
            int
        """
        return await self.collection.count_documents({})

    async def fetch(self, post:dict) -> dict:
        """Returns the data found in the collection.

        Args:
            post (dict): Should match the mongo db schema

        Returns:
            dict: The data about the user
        """
        return await self.collection.find_one(post)

    @property
    def fetch_all(self) -> AsyncIOMotorCursor:
        """Returns all the documents in the collection

        Returns:
            [AsyncIOMotorCursor]: The AsyncIOMotorCursor
        """
        return self.collection.find({})


    @property
    async def fetch_last(self) -> dict:
        """Returns the last document in the collection

        Returns:
            dict: The last document in the collection
        """
        return await self.fetch({"_id":{"$eq":await self.count}})

    def fetch_many(self, post:dict) -> AsyncIOMotorCursor:
        """Finds all documents in the collection based on the post

        Args:
            post (dict): The filter which needs to be searched

        Returns:
            AsyncIOMotorCursor: The AsyncIOMotorCursor
        """
        return self.collection.find(post)

    
    async def insert(self, post:dict) -> InsertOneResult:
        """Inserts a document in the collection

        Args:
            post (dict): The dictionary that needs to be inserted

        Returns:
            InsertOneResult: An instance pymongo.results.InsertOneResult
                                • inserted_id: The inserted document’s _id.
                                • acknowledged: `bool`
        """
        return await self.collection.insert_one(post)

    async def update(self, old:dict, new:dict) -> UpdateResult:
        """Updates the document in the collection

        Args:
            old (dict): The old data
            new (dict): The new data

        Returns:
            UpdateResult: An instance of pymongo.results.UpdateResult
                            • acknowledged: `bool`
                            • matched_count: The number of documents matched for this update.
                            • modified_count: The number of documents modified.
                            • raw_result: The raw result document returned by the server.
                            • upserted_id: The _id of the inserted document if an upsert took place. Otherwise `None`. 
        """
        return await self.collection.update_one(old, {"$set":new})

    async def delete(self, post:dict) -> DeleteResult:
        """Deletes the document from the collection

        Args:
            post (dict): The data to be deleted

        Returns:
            DeleteResult: An instance of pymongo.results.DeleteResult
                            • acknowledged: `bool` 
                            • deleted_count: The number of documents deleted.
                            • raw_result: The raw result document returned by the server.
        """
        return await self.collection.delete_one(post)