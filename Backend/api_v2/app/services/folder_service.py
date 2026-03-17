# Backend/api_v2/app/services/folder_service.py

from datetime import datetime, timezone
from typing import Optional, List

from bson import ObjectId
from pymongo.asynchronous.database import AsyncDatabase

from .chat_service import ChatService

from ..core import errors
from ..models.user_models import UserInDB
from ..models.folder_models import (
    FolderCreate, 
    FolderInDB,
    )

SESSIONS_COLLECTION = "chat_sessions"
FOLDERS_COLLECTION = "folders"


class FolderService:
    def __init__(self, db: AsyncDatabase):
        self._db = db

    @property
    def folders(self):
        return self._db[FOLDERS_COLLECTION]
    
    @property
    def chats(self):
        return self._db[SESSIONS_COLLECTION]
    

    # ----- Folders -----
    
    async def list_folders(
            self, 
            user: UserInDB,
    ) -> List[FolderInDB]:
        try:
            query = {"owner_id": user.id}
            cursor = self.folders.find(query).sort("created_at", 1)

            entries: List[FolderInDB] = []
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                entries.append(FolderInDB(**doc))

            return entries
        except TypeError:
            raise ValueError(errors.UNKNOWN_ERROR_0)


    async def get_by_id(
            self, 
            user: UserInDB,
            folder_id: str
    ) -> FolderInDB:
        doc = await self.folders.find_one(
            {"_id": ObjectId(folder_id), "owner_id": user.id}
        )
        if not doc:
            raise ValueError(errors.FOLDER_1000_NOT_FOUND)
        
        doc["_id"] = str(doc["_id"])
        return FolderInDB(**doc)
    
    
    async def get_by_title(
            self,
            user: UserInDB,
            folder_title: str,
    ) -> FolderInDB:
        doc = await self.folders.find_one(
            {"title": folder_title, "owner_id": user.id}
        )
        if not doc:
            return None
        
        doc["_id"] = str(doc["_id"])
        return FolderInDB(**doc)
    

    async def create_folder(
            self, 
            user: UserInDB, 
            folder_in: FolderCreate
    ) -> FolderInDB:
        now = datetime.now(timezone.utc)

        folder = await self.get_by_title(user, folder_in.title)
        if folder:
            raise ValueError(errors.FOLDER_1001_NAME_EXISTS)
        
        doc = {
            "owner_id": user.id,
            "title": folder_in.title,
            "created_at": now,
        }
        result = await self.folders.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return FolderInDB(**doc)
    

    async def delete_folder(
            self, 
            user: UserInDB, 
            folder_id: str,
            chat_service: ChatService
    ) -> None:
        # Ensure folder exists and belongs to the user
        await self.get_by_id(user, folder_id)

        # Deleta all chats inside this folder
        child_chats = self.chats.find({"folder_id": folder_id})
        async for cc in child_chats:
            try:
                await chat_service.delete_chat(user=user, chat_id=str(cc["_id"]))
            except ValueError:
                continue
        
        # Delete folder itself
        await self.folders.delete_one({"_id": ObjectId(folder_id), "owner_id": user.id})