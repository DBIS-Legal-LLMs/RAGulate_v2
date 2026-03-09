# Backend/api_v2/app/services/folder_service.py

from datetime import datetime, timezone
from typing import Optional, List

from fastapi import Depends

from bson import ObjectId
from pymongo.asynchronous.database import AsyncDatabase

from ..core import errors
from ..models.user_models import UserInDB
from ..models.folder_models import (
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


    async def get_by_id(
            self, 
            user: UserInDB,
            folder_id: str
    ) -> Optional[FolderInDB]:
        doc = await self.folders.find_one(
            {"_id": ObjectId(folder_id), "owner_id": user.id}
        )
        if not doc:
            raise ValueError(errors.FOLDER_1000_NOT_FOUND)
        
        doc["_id"] = str(doc["_id"])
        return FolderInDB(**doc)
    

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
                    user=user,
                    folder_id=folder_in.parent_folder_id
            )
            parent_depth = parent.depth

        depth = parent_depth + 1
        if depth > MAX_FOLDER_DEPTH:
            raise ValueError(errors.FOLDER_1002_MAX_DEPTH_EXCEEDED)
        
        doc = {
            "owner_id": user.id,
            "title": folder_in.title,
            "parent_folder_id": folder_in.parent_folder_id,
            "depth": depth,
            "created_at": now,
        }
        result = await self.folders.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return FolderInDB(**doc)
    
    
    async def update_depth(
            self,
            folder_id: str,
            parent_depth: int,

    ):
        new_depth = parent_depth + 1
        # Update this folder
        await self.folders.update_one(
            {"_id": ObjectId(folder_id)},
            {"$set": {"depth": new_depth}},
        )

        # Update children aswell
        query = {"parent_folder_id": folder_id}
        child_folders = self.folders.find(query)
        async for cf in child_folders:
            await self.update_depth(
                folder_id=str(cf["_id"]),
                parent_depth=new_depth
            )
    

    async def move_folder(
            self,
            user: UserInDB,
            folder_id: str,
            new_parent_id: Optional[str],
    ) -> FolderInDB:
        # Ensure folder exists
        folder = await self.get_by_id(user, folder_id)

        # Prevent moving into same parent again
        if folder.parent_folder_id == new_parent_id:
            raise ValueError(errors.FOLDER_1003_BOOTSTRAP_PARADOX)
        
        # Prevent moving into itself
        if folder_id == new_parent_id:
            raise ValueError(errors.FOLDER_1003_BOOTSTRAP_PARADOX)
        
        # Prevent moving into own child
        query = {"parent_folder_id": folder_id}
        child_folders = self.folders.find(query)
        async for cf in child_folders:
            child_id = str(cf["_id"])
            if child_id == new_parent_id:
                raise ValueError(errors.FOLDER_1003_BOOTSTRAP_PARADOX)
            query = {"parent_folder_id": child_id}
            grandchild_folders = self.folders.find(query)
            async for gcf in grandchild_folders:
                grandchild_id = str(cf["_id"])
                if grandchild_id == new_parent_id:
                    raise ValueError(errors.FOLDER_1003_BOOTSTRAP_PARADOX)

        # Determine depth (no parent -> 0 + 1, parent -> parent + 1)
        parent_depth = 0
        if new_parent_id:
            parent = await self.get_by_id(user, new_parent_id)
            parent_depth = parent.depth

        # Depth >= 4
        new_depth = parent_depth + 1
        if new_depth > MAX_FOLDER_DEPTH:
            raise ValueError(errors.FOLDER_1002_MAX_DEPTH_EXCEEDED)
        
        # Update this folder
        await self.folders.update_one(
            {"_id": ObjectId(folder_id)},
            {"$set": 
                {
                    "parent_folder_id": new_parent_id,
                    "depth": new_depth
                }
            },
        )

        # Update children depths (recursively)
        query = {"parent_folder_id": folder_id}
        child_folders = self.folders.find(query)
        async for cf in child_folders:
            await self.update_depth(
                folder_id=str(cf["_id"]),
                parent_depth=new_depth
            )

        return await self.get_by_id(user, folder_id)
    

    async def delete_folder(
            self, 
            user: UserInDB, 
            folder_id: str,
            chat_service: ChatService
    ) -> None:
        # Find all child-chats and delete each of them
        query = {"folder_id": folder_id}
        child_chats = self.chats.find(query)
        async for cc in child_chats:
            try:
                await chat_service.delete_chat(
                    user=user,
                    chat_id=str(cc["_id"])
                )
            except ValueError:
                continue   

        # Find all child-folders and delete each of them
        query = {"parent_folder_id": folder_id}
        child_folders = self.folders.find(query)
        async for cf in child_folders:
            try:
                await self.delete_folder(
                    user=user,
                    folder_id=str(cf["_id"]),
                    chat_service=chat_service
                )
            except ValueError:
                continue
        
        # In the end, delete the folder we are currently in
        await self.folders.delete_one(
            {"_id": ObjectId(folder_id),
             "owner_id": user.id}
        )
        return