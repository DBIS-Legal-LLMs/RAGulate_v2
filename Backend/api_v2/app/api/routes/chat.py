# Backend/api_v2/app/api/router/chat.py

from fastapi import APIRouter, Depends, HTTPException, status

from ...core.deps import get_current_user, get_db
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

router = APIRouter(prefix="", tags=["chat"])


def get_chat_service(db = Depends(get_db)) -> ChatService:
    return ChatService(db)


# ----- Sessions -----

@router.post(
    "/chat",
    response_model= ChatSessionPublic,
    status_code= status.HTTP_201_CREATED,
)
async def create_chat(
    data: ChatSessionCreate,
    current_user: UserInDB = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    session = await chat_service.create_chat(current_user, data)
    return ChatSessionPublic(
        id= session.id,
        title= session.title,
        folder_id=session.folder_id,
        created_at= session.created_at,
        updated_at= session.updated_at,
    )


@router.get(
    "/chats",
    response_model= list[ChatSessionPublic],
)
async def list_chats(
    current_user: UserInDB = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    sessions = await chat_service.list_chats(current_user)
    return [
        ChatSessionPublic(
            id= s.id,
            title= s.title,
            folder_id= s.folder_id,
            created_at= s.created_at,
            updated_at= s.updated_at,
        )
        for s in sessions
    ]


@router.get(
    "/chat/{chat_id}",
    response_model= ChatSessionWithMessages,
)
async def get_chat(
    chat_id: str,
    current_user: UserInDB = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    result = await chat_service.get_chat_with_messages(current_user, chat_id)

    if not result:
        raise HTTPException(
            status_code= status.HTTP_404_NOT_FOUND,
            detail= "Session not found",
        )
    
    return result

@router.delete(
    "/chat/{chat_id}",
    status_code= status.HTTP_204_NO_CONTENT,
)
async def delete_chat(
    chat_id: str,
    current_user: UserInDB = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    try:
        await chat_service.delete_chat(current_user, chat_id)
    except ValueError:
        raise HTTPException(
            status_code= status.HTTP_404_NOT_FOUND,
            detail= "Session not found",
        )


# ----- Messages -----

@router.post(
    "/chat/{chat_id}/messages",
    response_model= ChatTurnPublic,
    status_code= status.HTTP_201_CREATED,
)
async def post_messages(
    chat_id: str,
    data: MessageCreate,
    current_user: UserInDB = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    # aktuell nur User-Nachrichten speichern
    try:
        # turn = await chat_service.chat_with_rag(
        #     user= current_user,
        #     chat_id= chat_id,
        #     data= data,
        # )
        
        # Echo Chat ohne RAG
        turn = await chat_service.chat_echo(
            user= current_user,
            chat_id= chat_id,
            data= data,
        )
    except ValueError:
        raise HTTPException(
            status_code= status.HTTP_404_NOT_FOUND,
            detail= "Session not found",
        )
    
    return turn
