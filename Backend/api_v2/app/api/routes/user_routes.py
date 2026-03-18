# Backend/api_v2/app/api/routes/user_routes.py

from fastapi import APIRouter, Depends, HTTPException, status

from ...core.deps import get_current_user, get_db
from ...core import errors
from ...models.user_models import UserInDB, UserPublic
from ...services.user_service import UserService


router = APIRouter(prefix="/user", tags=["user"])


def get_user_service(db = Depends(get_db)) -> UserService:
    return UserService(db)


@router.put("/change-name", response_model=UserPublic, status_code=status.HTTP_200_OK)
async def change_username(
    new_username: str,
    current_user: UserInDB = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    try:
        user = await user_service.change_username(
            user=current_user,
            new_username=new_username,
        )
        return UserPublic(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            username=user.username,
            role=user.role,
            preferred_llm_provider=user.preferred_llm_provider,
            preferred_model=user.preferred_model,
            created_at=user.created_at,
        )
    except ValueError as code:
        if code == errors.USER_11_USERNAME_EXISTS:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User to rename not found")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not change username")