# Backend/api_v2/app/models/chat.py

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ----- Sessions -----

class ChatSessionCreate(BaseModel):
    title: str | None = None

class ChatSessionInDB(BaseModel):
    # MongoDB-ID as String, alias "_id"
    id: str | None = Field(default=None, alias="_id")
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True # erlaubt Nutzung von "id" <-> "_id"

class ChatSessionPublic(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


# ----- Messages -----

class MessageCreate(BaseModel):
    content: str

class MessageInDB(BaseModel):
    id: str | None = Field(default=None, alias="_id")
    session_id: str
    user_id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime

    class Config:
        populate_by_name = True

class MessagePublic(BaseModel):
    id: str
    session_id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


# ----- Kombi View -----

class ChatSessionWithMessages(BaseModel):
    session: ChatSessionPublic
    messages: list[MessagePublic]