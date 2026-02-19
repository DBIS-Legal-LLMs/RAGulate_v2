# Backend/api_v2/app/services/folder_service.py

from datetime import datetime, timezone
from typing import Optional, List

from fastapi import Depends

from bson import ObjectId
from pymongo.asynchronous.database import AsyncDatabase

from ..core import errors
from ..models.user import UserInDB
from ..models.folder import (
    FolderCreate, 
    FolderInDB,
    )

from .chat_service import ChatService

SESSIONS_COLLECTION = "chat_sessions"
FOLDERS_COLLECTION = "folders"
MAX_FOLDER_DEPTH = 3

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
            folder_id: Optional[str] = None,
    ) -> List[FolderInDB]:
        try:
            query = {"owner_id": user.id, 
                    "parent_folder_id": folder_id}
            cursor = self.folders.find(query).sort("created_at", 1)

            entries: List[FolderInDB] = []
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                entries.append(FolderInDB(**doc))

            return entries
        except TypeError:
            raise ValueError(errors.UNKNOWN_ERROR_0)
    

    async def create_folder(
            self, 
            user: UserInDB, 
            folder_in: FolderCreate
    ) -> FolderInDB:
        # time
        now = datetime.now(timezone.utc)

        # check parent + calculate depth
        parent_depth = 0
        if folder_in.parent_folder_id:
            parent = await self.get_by_id(
                    folder_id=folder_in.parent_folder_id, 
                    owner_id=user.id
            )
            if not parent:
                raise ValueError(errors.FOLDER_1000_NOT_FOUND)
            parent_depth = parent.depth

        depth = parent_depth + 1
        if depth > MAX_FOLDER_DEPTH:
            raise ValueError(errors.FOLDER_1002_MAX_DEPTH_EXCEEDED)
        
        doc = {
            "owner_id": user.id,
            "name": folder_in.name,
            "parent_id": folder_in.parent_folder_id,
            "depth": depth,
            "created_at": now,
        }
        result = await self.folders.insert_one(doc)
        doc["_id"] = str(result.inserted_id)

        return FolderInDB(**doc)


    async def get_by_id(
            self, 
            user: UserInDB,
            folder_id: str
    ) -> Optional[FolderInDB]:
        doc = await self.folders.find_one(
            {"_id": ObjectId(folder_id), "owner_id": user.id}
        )
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return FolderInDB(**doc)
    

    async def delete_folder(
            self, 
            current_user: UserInDB, 
            folder_id: str,
            chat_service: ChatService
    ) -> None:
        '''
        # delete only if empty (no subfolders)
        child = await self.collection.find_one(
            {"owner_id": owner_id, "parent_id": folder_id}
        )
        if child:
            raise ValueError("FOLDER_NOT_EMPTY")
        '''
        # Find all child-chats and delete each of them
        query = {"folder_id": folder_id}
        child_chats = self.chats.find(query)
        async for cc in child_chats:
            try:
                await chat_service.delete_chat(
                    chat_id=str(cc["_id"]),
                    user=current_user,
                    chat_service=chat_service
                )
            except ValueError:
                continue   

        # Find all child-folders and delete each of them
        query = {"parent_folder_id": folder_id}
        child_folders = self.folders.find(query)
        async for cf in child_folders:
            try:
                await self.delete_folder(
                    current_user=current_user,
                    folder_id=str(cf["_id"]),
                    chat_service=chat_service
                )
            except ValueError:
                continue