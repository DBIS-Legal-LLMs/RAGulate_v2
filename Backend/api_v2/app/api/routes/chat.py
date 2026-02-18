# Backend/api_v2/app/api/router/chat.py

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from ...core.deps import get_current_user, get_db
from ...core import errors
from ...models.user import UserInDB
from ...models.chat import (
    ChatSessionCreate,
    ChatSessionPublic,
    ChatSessionWithMessages,
    MessageCreate,
    MessagePublic,
    ChatTurnPublic
)
from ...services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


def get_chat_service(db = Depends(get_db)) -> ChatService:
    return ChatService(db)


# ----- Chats -----

@router.post(
    "",
    response_model= ChatSessionPublic,
    status_code= status.HTTP_201_CREATED,
)
async def create_chat(
    data: ChatSessionCreate,
    current_user: UserInDB = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    try:
        session = await chat_service.create_chat(current_user, data)
        return ChatSessionPublic(
            id= session.id,
            title= session.title,
            folder_id=session.folder_id,
            created_at= session.created_at,
            updated_at= session.updated_at,
        )
    except ValueError as code:
        if code =="":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=""
            )
        #if code == errors.UNKNOWN_ERROR_0
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="[UNKNOWN ERROR] Could not create chat"
        )


@router.get(
        "list", 
        response_model= list[ChatSessionPublic],
        status_code= status.HTTP_200_OK,
        )
async def list_chats(
    parent_id: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    try:
        chats = await chat_service.list_chats(
                user=current_user, 
                folder_id=parent_id
        )
        return [
            ChatSessionPublic(
                id= c.id,
                title= c.title,
                folder_id= c.folder_id,
                created_at= c.created_at,
                updated_at= c.updated_at,
            )
            for c in chats
        ]
    except ValueError as code:
        #if code == errors.UNKNOWN_ERROR_0
        raise ValueError("[UNKNOWN ERROR] Can't list chats")


@router.get(
        "/{chat_id}",
        response_model= ChatSessionWithMessages,
        status_code= status.HTTP_200_OK,
)
async def get_chat(
    chat_id: str,
    current_user: UserInDB = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    try:
        result = await chat_service.get_chat_with_messages(current_user, chat_id)
        return result
    except ValueError as code:
        if code == errors.CHAT_100_NOT_FOUND:
            raise HTTPException(
                status_code= status.HTTP_404_NOT_FOUND,
                detail= "Chat not found",
            )
        #if code == errors.UNKNOWN_ERROR_0:
        raise HTTPException(
            status_code= status.HTTP_400_BAD_REQUEST,
            detail= "[UNKNOWN ERROR] Can't get chat",
        )


@router.delete(
        "/{chat_id}", 
        status_code= status.HTTP_200_OK,
        )
async def delete_chat(
    chat_id: str,
    current_user: UserInDB = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    try:
        await chat_service.delete_chat(
            user=current_user, 
            chat_id=chat_id,
        )
        return {"status": "ok"}
    except ValueError as code:
        if code == errors.CHAT_100_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found"
            )
        #if code == errors.UNKNOWN_ERROR_0
        raise HTTPException(
            status_code= status.HTTP_400_NOT_FOUND,
            detail= "[UNKNOWN ERROR] Could not delete chat",
        )


# ----- Messages -----

@router.post(
        "/{chat_id}/messages",
        response_model= ChatTurnPublic,
        status_code= status.HTTP_200_OK,
)
async def post_messages(
    chat_id: str,
    data: MessageCreate,
    current_user: UserInDB = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    try:
        # Echo Chat ohne RAG
        turn = await chat_service.chat_echo(
            user= current_user,
            session_id= chat_id,
            data= data,
        )
        return turn
    except ValueError as code:
        if code == errors.CHAT_100_NOT_FOUND:
            raise HTTPException(
                status_code= status.HTTP_404_NOT_FOUND,
                detail= "Chat not found",
            )
        #if code == errors.UNKNOWN_ERROR_0:
        raise HTTPException(
            status_code= status.HTTP_400_BAD_REQUEST,
            detail= "[UNKNOWN ERROR] Could not post message",
        )
