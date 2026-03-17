# Backend/api_v2/app/models/chat.py

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ----- Sessions -----

class ChatSessionCreate(BaseModel):
    title: Optional[str] = None
    folder_id: Optional[str] = None


class ChatSessionInDB(BaseModel):
    # MongoDB-ID as String, alias "_id"
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    title: str
    folder_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True # erlaubt Nutzung von "id" <-> "_id"


class ChatSessionPublic(BaseModel):
    id: str
    title: str
    folder_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ----- Messages -----

class MessageCreate(BaseModel):
    content: str


class MessageInDB(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    chat_id: str
    user_id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime

    class Config:
        populate_by_name = True


class MessagePublic(BaseModel):
    id: str
    chat_id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime

    @classmethod
    def from_db(
        cls,
        msg: "MessageInDB"
    ) -> "MessagePublic":
        return cls(
            id= msg.id,
            chat_id= msg.chat_id,
            role= msg.role,
            content= msg.content,
            created_at= msg.created_at,
        )


# ----- Kombi View -----

# !!! Currently not used, but maybe interesting/useful later !!!

class ChatSessionWithMessages(BaseModel):
    chat: ChatSessionPublic
    messages: list[MessagePublic]

class ChatTurnPublic(BaseModel):
    user_message: MessagePublic
    assistant_message: MessagePublic
