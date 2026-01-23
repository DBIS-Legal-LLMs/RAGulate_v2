# Backend/api_v2/app/services/folder_service.py

from datetime import datetime, timezone
from typing import Optional, List

from bson import ObjectId
from pymongo.asynchronous.database import AsyncDatabase

from ..models.folder import FolderCreate, FolderInDB

FOLDERS_COLLECTION = "folders"
MAX_FOLDER_DEPTH = 3

class FolderService:
    def __init__(self, db: AsyncDatabase):
        self.__db = db

    @property
    def collection(self):
        return self.__db[FOLDERS_COLLECTION]
    
    async def get_by_id(self, folder_id: str, owner_id: str) -> Optional[FolderInDB]:
        doc = await self.collection.find_one(
            {"_id": ObjectId(folder_id), "owner_id": owner_id}
        )
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])
        return FolderInDB(**doc)
    
    async def list_folders(
            self, owner_id: str, parent_id: Optional[str] = None
    ) -> List[FolderInDB]:
        cursor = (
            self.collection.find({"owner_id": owner_id, "parent_id": parent_id})
            .sort("created_at", 1)
        )
        out: List[FolderInDB] = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            out.append(FolderInDB(**doc))
        return out
    
    async def create_folder(self, owner_id: str, folder_in: FolderCreate) -> FolderInDB:
        # check parent + calculate depth
        parent_depth = 0
        if folder_in.parent_id:
            parent = await self.get_by_id(folder_id=folder_in.parent_id, owner_id=owner_id)
            if not parent:
                raise ValueError("PARENT_NOT_FOUND")
            parent_depth = parent.depth

        depth = parent_depth + 1
        if depth > MAX_FOLDER_DEPTH:
            raise ValueError("MAX_DEPTH_EXCEEDED")
        
        # Optional: folder-name must be unique in same parent-level
        # existing = await self.collection.find_one(
        #    {
        #        "owner_id": owner_id,
        #        "parent_id": folder_in.parent_id,
        #        "name": folder_in.name,
        #    }
        #)
        #if existing: 
        #    raise ValueError("FOLDER_NAME_EXISTS")

        now = datetime.now(timezone.utc)
        doc = {
            "owner_id": owner_id,
            "name": folder_in.name,
            "parent_id": folder_in.parent_id,
            "depth": depth,
            "created_at": now,
        }
        result = await self.collection.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return FolderInDB(**doc)
    
    async def delete_folder(self, owner_id: str, folder_id: str) -> None:
        # delete only if empty (no subfolders)
        child = await self.collection.find_one(
            {"owner_id": owner_id, "parent_id": folder_id}
        )
        if child:
            raise ValueError("FOLDER_NOT_EMPTY")
        
        res = await self.collection.delete_one(
            {"_id": ObjectId(folder_id), "owner_id": owner_id}
        )
        if res.deleted_count == 0:
            raise ValueError("FOLDER_NOT_FOUND")