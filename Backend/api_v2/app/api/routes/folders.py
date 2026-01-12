# Backend/api_v2/app/api/router/folders.py

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from ...core.deps import get_current_user, get_db
from ...models.user import UserInDB
from ...models.folder import (
    FolderCreate, 
    FolderPublic
)
from ...services.folder_service import FolderService

router = APIRouter(prefix="/folders", tags=["folders"])


def get_folder_service(db = Depends(get_db)) -> FolderService:
    return FolderService(db)


@router.post("", response_model=FolderPublic, status_code=status.HTTP_201_CREATED)
async def create_folder(
    data: FolderCreate,
    current_user: UserInDB = Depends(get_current_user),
    folder_service: FolderService = Depends(get_folder_service),
):
    try:
        f = await folder_service.create_folder(owner_id=current_user.id, folder_in=data)
        return FolderPublic(
            id= f.id,
            name= f.name,
            parent_id= f.parent_id,
            depth= f.depth,
            created_at= f.created_at,
        )
    except ValueError as e:
        code = str(e)
        if code == "PARENT_NOT_FOUND":
            raise HTTPException(status_code=404, detail="Parent folder not found")
        if code == "MAX_DEPTH_EXCEEDED":
            raise HTTPException(status_code=400, detail="Max folder depth is 3")
        if code == "FOLDER_NAME_EXISTS":
            raise HTTPException(status_code=400, detail="Folder name already exists")
        
        raise HTTPException(status_code=400, detail="[UNKNOWN ERROR] Could not create folder")
    

@router.get("list", response_model=list[FolderPublic])
async def list_folders(
    parent_id: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_user),
    folder_service: FolderService = Depends(get_folder_service),
):
    folders = await folder_service.list_folders(owner_id=current_user.id, parent_id=parent_id)
    return [
        FolderPublic(
            id= f.id,
            name= f.name,
            parent_id= f.parent_id,
            depth= f.depth,
            created_at= f.created_at,
        )
        for f in folders
    ]


@router.delete("/{folder_id}")
async def delete_folder(
    folder_id: str,
    current_user: UserInDB = Depends(get_current_user),
    folder_service: FolderService = Depends(get_folder_service),
):
    try:
        await folder_service.delete_folder(owner_id=current_user.id, folder_id=folder_id)
        return {"status": "ok"}
    except ValueError as e:
        code = str(e)
        if code == "FOLDER_NOT_EMPTY":
            raise HTTPException(status_code=400, detail="Folder not empty")
        if code == "FOLDER_NOT_FOUND":
            raise HTTPException(status_code=404, detail="Folder not found")
        
        raise HTTPException(status_code=400, detail="[UNKNOWN ERROR] Could not delete folder")