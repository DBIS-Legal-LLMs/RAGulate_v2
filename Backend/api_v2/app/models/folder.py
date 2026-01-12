# Backend/api_v2/app/models/folder.py

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class FolderBase(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    parent_id: Optional[str] = None

class FolderCreate(FolderBase):
    pass

class FolderInDB(FolderBase):
    id: Optional[str] = Field(default=None, alias="_id")
    owner_id: str
    depth: int
    created_at: datetime

    class Config:
        populate_by_name = True

class FolderPublic(FolderBase):
    id: str
    depth: int
    created_at: datetime