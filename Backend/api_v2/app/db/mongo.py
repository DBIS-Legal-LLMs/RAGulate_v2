# Backend/api_v2/app/db/mongo.py

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from ..config import get_settings

_settings = get_settings()
_client: AsyncIOMotorClient | None = None

def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(_settings.mongo_url)
    return _client

def get_database() -> AsyncIOMotorDatabase:
    client = get_client()
    return client[_settings.mongo_db_name]