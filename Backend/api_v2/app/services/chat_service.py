# Backend/api_v2/app/services/chat_service.py

import asyncio
import json
from datetime import datetime, timezone
from typing import AsyncGenerator, List, Optional

from bson import ObjectId
from pymongo.asynchronous.database import AsyncDatabase

from ..core import errors
from ..models.user_models import UserInDB
from ..models.chat_models import (
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
    

    async def move_chat(
            self,
            user: UserInDB,
            chat_id: str,
            new_folder_id: Optional[str],
    ) -> ChatSessionInDB:
        # Ensure chat exists & belongs to user
        chat = await self.get_chat_for_user(user, chat_id)

        # Update folder_id
        await self.chats.update_one(
            {"_id": ObjectId(chat_id)},
            {"$set": {"folder_id": new_folder_id}},
        )

        # Return updated chat
        updated = await self.get_chat_for_user(user, chat_id)
        return updated
    

    async def change_name(
            self,
            user: UserInDB,
            chat_id: str,
            new_title: str,
    ) -> ChatSessionInDB:
        # Ensure chat exists & belongs to user
        chat = await self.get_chat_for_user(user, chat_id)

        # Update name
        await self.chats.update_one(
            {"_id": ObjectId(chat_id)},
            {"$set": {"title": new_title}},
        )

        # Return updated chat
        updated = await self.get_chat_for_user(user, chat_id)
        return updated
    
    
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
    

    # ----- LLM Echo Chat -----

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
    

    # ----- LLM streaming chat -----


    async def _run_llm_and_persist(
            self,
            user: UserInDB,
            chat_id: str,
            data: MessageCreate,
            chunk_queue: asyncio.Queue,
    ) -> None:
        """
        Runs the full LLM call and persists both messages to the DB.
        Runs inside asyncio.shield() so client disconnects cannot cancel it.

        Puts each text chunk onto chunk_queue as {"type": "chunk", "content": str}
        Puts {"type": "done", ...} as the final item.
        Puts {"type": "error", "content": str} if the LLM call fails.
        The SSE generator reads from this queue and forwards to the client.
        """
        now = datetime.now(timezone.utc)

        # 1) Persist user message
        user_doc = {
            "chat_id": chat_id,
            "user_id": user.id,
            "role": "user",
            "content": data.content,
            "created_at": now,
        }
        result_user = await self.messages.insert_one(user_doc)
        user_msg_id = str(result_user.inserted_id)

        # 2) Build conversation history (includes the message we just saved)
        history = await self.list_messages_in_chat(user, chat_id)
        llm_history = [
            {"role": m.role, "content": m.content}
            for m in history
            if m.role in {"user", "assistant"}
        ]

        # 3) Stream LLM, forward chunks to queue, accumulate full answer
        full_answer: List[str] = []
        try:
            async for chunk in run_rag_query(
                question=data.content,
                history_messages=llm_history,
            ):
                full_answer.append(chunk)
                await chunk_queue.put({"type": "chunk", "content": chunk})

        except Exception as exc:
            # LLM failed - surface a clean error event, do not persist
            await chunk_queue.put({"type": "error", "content": str(exc)})
            return
    
        # 4) Persist the complete assistant message
        assembled = "".join(full_answer)
        now_assistant = datetime.now(timezone.utc)
        assistant_doc = {
            "chat_id": chat_id,
            "user_id": user.id,
            "role": "assistant",
            "content": assembled,
            "created_at": now_assistant,
        }
        result_assistant = await self.messages.insert_one(assistant_doc)
        assistant_msg_id = str(result_assistant.inserted_id)

        # 5) Update session timestamp
        await self.chats.update_one(
            {"_id": ObjectId(chat_id)},
            {"$set": {"updated_at": now_assistant}}
        )

        # 6) Signal completion
        await chunk_queue.put({
            "type": "done",
            "content": assembled,
            "user_message_id": user_msg_id,
            "assistant_message_id": assistant_msg_id,
        })
    

    async def _stream_generator(
            self,
            user: UserInDB,
            chat_id: str,
            data: MessageCreate,
    ) -> AsyncGenerator[str, None]:
        """
        SSE generator for the route.
 
        Spawns _run_llm_and_persist as a shielded background task so it
        completes and writes to the DB even if the client disconnects.
        This generator just reads from the shared queue and forwards events.
        Once the client disconnects, this generator is cancelled but the
        background task keeps running to completion.
        """
        chunk_queue: asyncio.Queue = asyncio.Queue()

        # asyncio.shield() prevents the task from being cancelled when the
        # client disconnects and Starlette cancels the response coroutine.
        task = asyncio.ensure_future(
            asyncio.shield(
                self._run_llm_and_persist(user, chat_id, data, chunk_queue)
            )
        )

        try:
            while True:
                event = await chunk_queue.get()

                if event["type"] == "chunk":
                    yield f"data: {json.dumps({'type': 'chunk', 'content': event['content']})}\n\n"

                elif event["type"] == "done":
                    yield f"data: {json.dumps({'type': 'done', 'content': event['content'], 'user_message_id': event['user_message_id'], 'assistant_message_id': event['assistant_message_id']})}\n\n"
                    break

                elif event["type"] == "error":
                    yield f"data: {json.dumps({'type': 'error', 'content': event['content']})}\n\n"
                    break
        
        except asyncio.CancelledError:
            # Client disconnected — stop forwarding but let the task finish.
            # The task is shielded so it will keep running and persist to DB.
            pass