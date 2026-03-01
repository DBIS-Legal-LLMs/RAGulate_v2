# Backend/api_v2/app/api/router/chat.py

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from ...core.deps import get_current_user, get_db
from ...core import errors
from ...models.user_models import UserInDB
from ...models.chat_models import (
    ChatSessionCreate,
    ChatSessionPublic,
    ChatSessionWithMessages,
    MessageCreate,
)
from ...services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


def get_chat_service(db = Depends(get_db)) -> ChatService:
    return ChatService(db)


# ----- Chats -----

@router.post("", response_model=ChatSessionPublic, status_code=status.HTTP_201_CREATED)
async def create_chat(
    data: ChatSessionCreate,
    current_user: UserInDB = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    try:
        session = await chat_service.create_chat(current_user, data)
        return ChatSessionPublic(
            id=session.id,
            title=session.title,
            folder_id=session.folder_id,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not create chat")


@router.get("/list", response_model=list[ChatSessionPublic], status_code=status.HTTP_200_OK)
async def list_chats(
    parent_id: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    try:
        chats = await chat_service.list_chats(user=current_user, folder_id=parent_id)
        return [
            ChatSessionPublic(
                id=c.id,
                title=c.title,
                folder_id=c.folder_id,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in chats
        ]
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not list chats")


@router.get("/{chat_id}", response_model=ChatSessionWithMessages, status_code=status.HTTP_200_OK)
async def get_chat(
    chat_id: str,
    current_user: UserInDB = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    try:
        return await chat_service.get_chat_with_messages(current_user, chat_id)
    except ValueError as exc:
        if str(exc) == str(errors.CHAT_100_NOT_FOUND):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not get chat")


@router.delete("/{chat_id}", status_code=status.HTTP_200_OK)
async def delete_chat(
    chat_id: str,
    current_user: UserInDB = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    try:
        await chat_service.delete_chat(user=current_user, chat_id=chat_id)
        return {"status": "ok"}
    except ValueError as exc:
        if str(exc) == str(errors.CHAT_100_NOT_FOUND):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not delete chat")


# ----- Messages -----

@router.post("/{chat_id}/messages", status_code=status.HTTP_200_OK)
async def post_message(
    chat_id: str,
    data: MessageCreate,
    current_user: UserInDB = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    Sends a user message and streams the assistant response as SSE.
 
        SSE event types:
      {"type": "chunk",  "content": "<delta>"}
          — one event per token/chunk as it streams in
 
      {"type": "done",   "content": "<full response>",
       "user_message_id": "<id>", "assistant_message_id": "<id>"}
          — final event, emitted after the full response is persisted to DB
 
      {"type": "error",  "content": "<reason>"}
          — emitted when the LLM is unavailable or returns an error

    If the client disconnects mid-stream, the backend continues the LLM
    call and persists the full response to the DB anyway. The frontend can
    retrieve the completed message via GET /api/chat/{chat_id}.
    """
    # Validate the chat exists before opening the stream, so we can still
    # return a proper HTTP 404 instead of an error mid-stream.
    try:
        await chat_service.get_chat_for_user(user=current_user, chat_id=chat_id)
    except ValueError as exc:
        if str(exc) == str(errors.CHAT_100_NOT_FOUND):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not send message")
 
    generator = chat_service._stream_generator(
        user=current_user,
        chat_id=chat_id,
        data=data,
    )
 
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            # Prevent proxies and browsers from buffering the stream
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )