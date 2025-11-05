# Backend/api_v2/app/api/routes/auth.py

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from ...models.user import UserCreate, UserPublic
from ...services.user_services import UserService
from ...core.security import create_access_token
from ...core.deps import get_user_service
from ...config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])
_settings = get_settings()

class TokenResponse(UserPublic):
    access_token: str
    token_type: str = "bearer"

@router.post("/register", response_model=UserPublic)
async def register(
    user_in: UserCreate,
    user_service: UserService = Depends(get_user_service),
):
    try:
        user = await user_service.create_user(user_in)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists",
        )
    return UserPublic(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        preferred_llm_provider=user.preferred_llm_provider,
        preferred_model=user.preferred_model,
        created_at=user.created_at,
    )

@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(get_user_service),
):
    user = await user_service.verify_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )

    access_token_expires = timedelta(
        minutes=_settings.jwt_access_token_expire_minutes
    )
    token = create_access_token(
        subject=str(user.id),
        expires_delta=access_token_expires,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "preferred_llm_provider": user.preferred_llm_provider,
            "preferred_model": user.preferred_model,
            "created_at": user.created_at.isoformat(),
        },
    }
