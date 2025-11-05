# Backend/api_v2/app/services/chat_service.py

from datetime import datetime, timezone
from typing import List, Optional

from bson import ObjectId
from pymongo.asynchronous.database import AsyncDatabase

from ..models.user import UserInDB
from ..models.chat import (
    ChatSessionCreate,
    ChatSessionInDB,
    ChatSessionPublic,
    MessageCreate,
    MessageInDB,
    MessagePublic,
    ChatSessionWithMessages,
    )

SESSIONS_COLLECTION = "chat_sessions"
MESSAGES_COLLECTION = "chat_messages"

class ChatService:
    def __init__(self, db: AsyncDatabase):
        self._db = db

    @property
    def sessions(self):
        return self._db[SESSIONS_COLLECTION]
    
    @property
    def messages(self):
        return self._db[MESSAGES_COLLECTION]
    

    # ----- Sessions -----

    async def create_session(
            self, 
            user: UserInDB, 
            data: ChatSessionCreate
    ) -> ChatSessionInDB:
        now = datetime.now(timezone.utc)
        doc = {
            "user_id": user.id,
            "title": data.title or "Neue Sitzung",
            "created_at": now,
            "updated_at": now,
        }
        result = await self.sessions.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        
        return ChatSessionInDB(**doc)
    

    async def list_sessions(
            self, 
            user: UserInDB
    ) -> list[ChatSessionInDB]:
        cursor = (
            self.sessions.find({"user_id": user.id})
            .sort("updated_at", -1)
        )
        docs: list[ChatSessionInDB] = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            docs.append(ChatSessionInDB(**doc))

        return docs
    

    async def get_session_for_user(
            self, 
            user: UserInDB, 
            session_id: str
            ) -> Optional[ChatSessionInDB]:
        doc = await self.sessions.find_one(
            {"_id": ObjectId(session_id), "user_id": user.id}
        )
        if not doc:
            return None
        doc["_id"] = str(doc["_id"])

        return ChatSessionInDB(**doc)
    

    # ----- Messages -----

    async def list_messages_for_session(
            self, 
            user: UserInDB, 
            session_id: str
    ) -> list[MessageInDB]:
        # Ensure session belongs to user
        session = await self.get_session_for_user(user, session_id)
        if not session:
            return []
        
        cursor = (
            self.messages.find({"session_id": session_id, "user_id": user.id})
            .sort("created_at", 1)
        )
        docs: list[MessageInDB] = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            docs.append(MessageInDB(**doc))

        return docs
    

    async def add_message(
            self,
            user: UserInDB,
            session_id: str,
            role: str,
            data: MessageCreate,
    ) -> MessageInDB:
        # ensure session exists & belongs to user
        session = await self.get_session_for_user(user, session_id)
        if not session:
            raise ValueError("Session not found or not owned by user")
        
        now = datetime.now(timezone.utc)
        doc = {
            "session_id": session_id,
            "user_id": user.id,
            "role": role,
            "content": data.content,
            "created_at": now,
        }
        result = await self.messages.insert_one(doc)
        doc["_id"] = str(result.inserted_id)

        # Session updaten
        await self.sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"updated_at": now}},
        )

        return MessageInDB(**doc)
    

    async def get_session_with_messages(
            self,
            user: UserInDB, 
            session_id: str
    ) -> Optional[ChatSessionWithMessages]:
        session = await self.get_session_for_user(user, session_id)
        if not session:
            return None
        msgs = await self.list_messages_for_session(user, session_id)

        session_public = ChatSessionPublic(
            id= session.id,
            title= session.title,
            created_at= session.created_at,
            updated_at= session.updated_at,
        )

        messages_public = [
            MessagePublic(
                id= m.id,
                session_id= m.session_id,
                role= m.role,
                content= m.content,
                created_at= m.created_at,
            )
            for m in msgs
        ]

        return ChatSessionWithMessages(
            session= session_public,
            messages= messages_public,
        )
