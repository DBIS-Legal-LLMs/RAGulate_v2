# Backend/api_v2/app/services/chat_service.py

from datetime import datetime, timezone
from typing import List, Optional

from bson import ObjectId
from pymongo.asynchronous.database import AsyncDatabase

from ..core import errors
from ..models.user import UserInDB
from ..models.chat import (
    ChatSessionCreate,
    ChatSessionInDB,
    ChatSessionPublic,
    MessageCreate,
    MessageInDB,
    MessagePublic,
    ChatSessionWithMessages,
    ChatTurnPublic,
)
from .rag_service import run_rag_query

SESSIONS_COLLECTION = "chat_sessions"
MESSAGES_COLLECTION = "chat_messages"


class ChatService:
    def __init__(self, db: AsyncDatabase):
        self._db = db

    @property
    def chats(self):
        return self._db[SESSIONS_COLLECTION]
    
    @property
    def messages(self):
        return self._db[MESSAGES_COLLECTION]
    

    # ----- Chats -----
    
    async def list_chats(
            self,
            user: UserInDB,
            folder_id: Optional[str] = None,
    ) -> List[ChatSessionInDB]:
        try:
            query = {"user_id": user.id}
            if folder_id is not None:
                query["folder_id"] = folder_id
            cursor = self.chats.find(query).sort("updated_at", -1)
 
            entries: List[ChatSessionInDB] = []
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                entries.append(ChatSessionInDB(**doc))
            return entries
        except TypeError:
            raise ValueError(errors.UNKNOWN_ERROR_0)


    async def create_chat(
            self,
            user: UserInDB,
            data: ChatSessionCreate,
    ) -> ChatSessionInDB:
        now = datetime.now(timezone.utc)
        doc = {
            "user_id": user.id,
            "folder_id": data.folder_id,
            "title": data.title or "Neuer Chat",
            "created_at": now,
            "updated_at": now,
        }
        result = await self.chats.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        return ChatSessionInDB(**doc)
    

    async def get_chat_for_user(
            self,
            user: UserInDB,
            chat_id: str,
    ) -> ChatSessionInDB:
        doc = await self.chats.find_one(
            {"_id": ObjectId(chat_id), "user_id": user.id}
        )
        if not doc:
            raise ValueError(errors.CHAT_100_NOT_FOUND)
        doc["_id"] = str(doc["_id"])
        return ChatSessionInDB(**doc)
    
    
    async def delete_chat(
            self, 
            user: UserInDB,
            chat_id: str
    ) -> None:
        # ensure chat exists & belongs to user
        await self.get_chat_for_user(user, chat_id)
        # delete chat
        await self.chats.delete_one({"_id": ObjectId(chat_id)})
        # delete all connected messages
        await self.messages.delete_many({"chat_id": chat_id})
    

    # ----- Messages -----

    async def list_messages_in_chat(
            self,
            user: UserInDB,
            chat_id: str,
    ) -> List[MessageInDB]:
        await self.get_chat_for_user(user, chat_id)
 
        cursor = self.messages.find(
            {"chat_id": chat_id, "user_id": user.id}
        ).sort("created_at", 1)
 
        entries: List[MessageInDB] = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            entries.append(MessageInDB(**doc))
        return entries
    

    async def get_chat_with_messages(
            self,
            user: UserInDB,
            chat_id: str,
    ) -> ChatSessionWithMessages:
        chat = await self.get_chat_for_user(user, chat_id)
 
        msgs = await self.list_messages_in_chat(user, chat_id)
 
        return ChatSessionWithMessages(
            chat=ChatSessionPublic(
                id=chat.id,
                title=chat.title,
                folder_id=chat.folder_id,
                created_at=chat.created_at,
                updated_at=chat.updated_at,
            ),
            messages=[
                MessagePublic(
                    id=m.id,
                    chat_id=m.chat_id,
                    role=m.role,
                    content=m.content,
                    created_at=m.created_at,
                )
                for m in msgs
            ],
        )
    

    # ----- LLM chat -----

    async def chat_echo(
            self,
            user: UserInDB,
            chat_id: str,
            data: MessageCreate,
    ) -> ChatTurnPublic:
        """
        Einfache Echo-Implementierung ohne RAG.
        Speichert die User-Nachricht und antwortet mit der gleichen Nachricht.
        """
        # 1) Session checken
        session = await self.get_chat_for_user(user, chat_id)
        if not session:
            raise ValueError(errors.CHAT_100_NOT_FOUND)
        
        now = datetime.now(timezone.utc)

        # 2) User-Message speichern
        user_doc = {
            "chat_id": chat_id,
            "user_id": user.id,
            "role": "user",
            "content": data.content,
            "created_at": now,
        }
        result_user = await self.messages.insert_one(user_doc)
        user_doc["_id"] = str(result_user.inserted_id)
        user_msg = MessageInDB(**user_doc)

        # 3) Assitant-Message (Echo) speichern
        now_assistant = datetime.now(timezone.utc)
        assistant_doc = {
            "chat_id": chat_id,
            "user_id": user.id,
            "role": "assistant",
            "content": data.content,  # Echo
            "created_at": now_assistant,
        }
        result_assistant = await self.messages.insert_one(assistant_doc)
        assistant_doc["_id"] = str(result_assistant.inserted_id)
        assistant_msg = MessageInDB(**assistant_doc)

        # Session-Updated Timestamp aktualisieren
        await self.chats.update_one(
            {"_id": ObjectId(chat_id)},
            {"$set": {"updated_at": now_assistant}},
        )

        return ChatTurnPublic(
            user_message= MessagePublic.from_db(user_msg),
            assistant_message= MessagePublic.from_db(assistant_msg),
        )


    async def chat_with_llm(
            self,
            user: UserInDB,
            chat_id: str,
            data: MessageCreate,
    ) -> ChatTurnPublic:
        """
        Persists the user message, sends the full conversation history to the
        LLM, then persists and returns the assistant reply.
        """
        await self.get_chat_for_user(user=user, chat_id=chat_id)

        now = datetime.now(timezone.utc)

        # 1) Persistent user message
        user_doc = {
            "chat_id": chat_id,
            "user_id": user.id,
            "role": "user",
            "content": data.content,
            "created_at": now,
        }
        result_user = await self.messages.insert_one(user_doc)
        user_doc["_id"] = str(result_user.inserted_id)
        user_msg = MessageInDB(**user_doc)

        # 2) Load full history (including the message we just saved)
        history = await self.list_messages_in_chat(user=user, chat_id=chat_id)
        llm_history = [
            {"role": m.role, "content": m.content}
            for m in history
            if m.role in {"user", "assistant"}
        ]

        # 3) Call LLM
        answer = await run_rag_query(
            question=data.content,
            history_messages=llm_history,
        )

        # 4) Persist assistant message (response)
        now_assistant = datetime.now(timezone.utc)
        assistant_doc = {
            "chat_id": chat_id,
            "user_id": user.id,
            "role": "assistant",
            "content": answer,
            "created_at": now_assistant,
        }
        result_assistant = await self.messages.insert_one(assistant_doc)
        assistant_doc["_id"] = str(result_assistant.inserted_id)
        assistant_msg = MessageInDB(**assistant_doc)

        # 5) Update session timestamp
        await self.chats.update_one(
            {"_id": ObjectId(chat_id)},
            {"$set": {"updated_at": now_assistant}},
        )

        return ChatTurnPublic(
            user_message=MessagePublic.from_db(user_msg),
            assistant_message=MessagePublic.from_db(assistant_msg),
        )