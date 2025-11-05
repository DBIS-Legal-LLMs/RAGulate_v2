# Backend/api_v2/app/db/mongo.py

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from ..config import get_settings

_settings = get_settings()
_client: AsyncMongoClient | None = None

def get_client() -> AsyncMongoClient:
    global _client
    if _client is None:
        _client = AsyncMongoClient(_settings.mongo_url)
    return _client

def get_database() -> AsyncDatabase:
    client = get_client()
    return client[_settings.mongo_db_name]