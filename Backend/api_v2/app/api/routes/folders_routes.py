# Backend/api_v2/app/api/router/folders.py

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from ...core.deps import get_current_user, get_db
from ...core import errors
from ...models.user_models import UserInDB
from ...models.folder_models import FolderCreate, FolderPublic
from ...services.folder_service import FolderService
from ...services.chat_service import ChatService

router = APIRouter(prefix="/folders", tags=["folders"])


def get_chat_service(db = Depends(get_db)) -> ChatService:
    return ChatService(db)


def get_folder_service(db = Depends(get_db)) -> FolderService:
    return FolderService(db)


@router.post(
        "", 
        response_model=FolderPublic, 
        status_code=status.HTTP_201_CREATED,
        )
async def create_folder(
    data: FolderCreate,
    current_user: UserInDB = Depends(get_current_user),
    folder_service: FolderService = Depends(get_folder_service),
):
    try:
        f = await folder_service.create_folder(user=current_user, folder_in=data)
        return FolderPublic(
            id= f.id,
            title= f.title,
            created_at= f.created_at,
        )
    except ValueError as code:
        if code == errors.FOLDER_1001_NAME_EXISTS:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail="Folder name already exists"
            )
        #if code == errors.UNKNOWN_ERROR_0
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Could not create folder"
        )
    

@router.get(
        "list", 
        response_model=list[FolderPublic], 
        status_code=status.HTTP_200_OK
        )
async def list_folders(
    current_user: UserInDB = Depends(get_current_user),
    folder_service: FolderService = Depends(get_folder_service),
):
    try:
        folders = await folder_service.list_folders(user=current_user)
        return [
            FolderPublic(
                id= f.id,
                title= f.title,
                created_at= f.created_at,
            )
            for f in folders
        ]
    except ValueError as code:
        #if code == errors.UNKNOWN_ERROR_0
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not list folders",
        )


@router.delete(
        "/{folder_id}", 
        status_code=status.HTTP_200_OK,
        )
async def delete_folder(
    folder_id: str,
    current_user: UserInDB = Depends(get_current_user),
    folder_service: FolderService = Depends(get_folder_service),
    chat_service: ChatService = Depends(get_chat_service)
):
    try:
        await folder_service.delete_folder(
                user=current_user, 
                folder_id=folder_id,
                chat_service=chat_service,
        )
        return {"status": "ok"}
    except ValueError as code:
        if code == errors.FOLDER_1000_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Folder not found"
            )
        #if code == errors.UNKNOWN_ERROR_0
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Could not delete folder"
        )