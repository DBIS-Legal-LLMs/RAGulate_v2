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
    ChatTurnPublic,
    )

from .rag_service import run_rag_query, LLMProviderName, DEFAULT_MODEL
from .folder_service import FolderService

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

    async def create_chat(
            self, 
            user: UserInDB, 
            data: ChatSessionCreate
    ) -> ChatSessionInDB:
        now = datetime.now(timezone.utc)

        folder_id = data.folder_id
        if folder_id:
            folder_service = FolderService(self._db)
            folder = await folder_service.get_by_id(folder_id=folder_id, owner_id=user.id)
            if not folder:
                raise ValueError("Folder not found or not owned by user")

        doc = {
            "user_id": user.id,
            "title": data.title or "Neue Sitzung",
            "created_at": now,
            "updated_at": now,
        }
        result = await self.sessions.insert_one(doc)
        doc["_id"] = str(result.inserted_id)
        
        return ChatSessionInDB(**doc)
    

    async def list_chats(
            self, 
            user: UserInDB,
            folder_id: str | None = None
    ) -> list[ChatSessionInDB]:
        query = {"user_id": user.id}
        if folder_id is not None:
            query["folder_id"] = folder_id # None = Root, without explicit folder

        cursor = self.sessions.find(query).sort("updated_at", -1)
        docs: list[ChatSessionInDB] = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            docs.append(ChatSessionInDB(**doc))

        return docs
    

    async def get_chat_for_user(
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
    
    
    async def delete_chat(
            self, 
            user: UserInDB,
            session_id: str
    ) -> None:
        session = await self.get_chat_for_user(user, session_id)
        if not session:
            raise ValueError("Session not found or not owned by user")
        
        # Session löschen
        await self.sessions.delete_one({"_id": ObjectId(session_id)})

        # Alle zugehörigen Messages löschen
        await self.messages.delete_many({"session_id": session_id})
    

    # ----- Messages -----

    async def list_messages_in_chat(
            self, 
            user: UserInDB, 
            session_id: str
    ) -> list[MessageInDB]:
        # Ensure session belongs to user
        session = await self.get_chat_for_user(user, session_id)
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
        session = await self.get_chat_for_user(user, session_id)
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
    

    async def get_chat_with_messages(
            self,
            user: UserInDB, 
            session_id: str
    ) -> Optional[ChatSessionWithMessages]:
        session = await self.get_chat_for_user(user, session_id)
        if not session:
            return None
        msgs = await self.list_messages_in_chat(user, session_id)

        session_public = ChatSessionPublic(
            id= session.id,
            title= session.title,
            folder_id= session.folder_id,
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
    

    # ----- Chat + LightRAG -----

    async def chat_echo(
            self,
            user: UserInDB,
            session_id: str,
            data: MessageCreate,
    ) -> ChatTurnPublic:
        """
        Einfache Echo-Implementierung ohne RAG.
        Speichert die User-Nachricht und antwortet mit der gleichen Nachricht.
        """
        # 1) Session checken
        session = await self.get_chat_for_user(user, session_id)
        if not session:
            raise ValueError("Session not found or not owned by user")
        
        now = datetime.now(timezone.utc)

        # 2) User-Message speichern
        user_doc = {
            "session_id": session_id,
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
            "session_id": session_id,
            "user_id": user.id,
            "role": "assistant",
            "content": data.content,  # Echo
            "created_at": now_assistant,
        }
        result_assistant = await self.messages.insert_one(assistant_doc)
        assistant_doc["_id"] = str(result_assistant.inserted_id)
        assistant_msg = MessageInDB(**assistant_doc)

        # Session-Updated Timestamp aktualisieren
        await self.sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"updated_at": now_assistant}},
        )

        return ChatTurnPublic(
            user_message= MessagePublic.from_db(user_msg),
            assistant_message= MessagePublic.from_db(assistant_msg),
        )

    async def chat_with_rag(
            self,
            user: UserInDB,
            session_id: str,
            data: MessageCreate,
    ) -> ChatTurnPublic:
        """
        Was passiert hier grob ?
        1. User-Nachricht speichern
        2. Historie laden und für LightRAG aufbereiten
        3. RAG-Query ausführen (Provider + Modell aus User-Settings)
        4. Assistant-Nachricht speichern
        5. Beide Nachrichten als ChatTurnPublic zurückgeben
        """
        # 1) Session checken
        session = await self.get_chat_for_user(user, session_id)
        if not session:
            raise ValueError("Session not found or not owned by user")
        
        now = datetime.now(timezone.utc)

        # 2) User-Message speichern
        user_doc = {
            "session_id": session_id,
            "user_id": user.id,
            "role": "user",
            "content": data.content,
            "created_at": now,
        }
        result_user = await self.messages.insert_one(user_doc)
        user_doc["_id"] = str(result_user.inserted_id)
        user_msg = MessageInDB(**user_doc)

        # 3) Historie laden (inkl. gerade gespeicherter User-Message)
        history = await self.list_messages_in_chat(user, session_id)

        lightrag_history = [
            {"role": m.role, "content": m.content}
            for m in history
            if m.role in {"user", "assitant"}
        ]

        # 4) Provider & Modell aus User-Settings oder Defaults bestimmen
        provider: LLMProviderName = (
            user.preferred_llm_provider or "huggingface"
        )
        model_name: str = user.preferred_model or DEFAULT_MODEL[provider]

        rag_answer = await run_rag_query(
            question= data.content,
            provider= provider,
            model= model_name,
            mode= "hybrid",
            response_type= "Multiple Paragraphs",
            user_prompt= None,
            history_messages= lightrag_history,
        )

        # 5) Assitant-Message speichern
        now_assistant = datetime.now(timezone.utc)
        assistant_doc = {
            "session_id": session_id,
            "user_id": user.id,
            "role": "assistant",
            "content": rag_answer,
            "created_at": now_assistant,
        }
        result_assistant = await self.messages.insert_one(assistant_doc)
        assistant_doc["_id"] = str(result_assistant.inserted_id)
        assistant_msg = MessageInDB(**assistant_doc)

        # Session-Updated Timestamp aktualisieren
        await self.sessions.update_one(
            {"_id": ObjectId(session_id)},
            {"$set": {"updated_at": now_assistant}},
        )

        return ChatTurnPublic(
            user_message= MessagePublic.from_db(user_msg),
            assistant_message= MessagePublic.from_db(assistant_msg),
        )
