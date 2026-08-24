# Backend/api_v2/app/core/deps.py

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from ..db.mongo import get_database
from .jwt_verification import verify_access_token
from ..models.auth_models import AuthenticatedUser

# tokenUrl is only used to populate the OpenAPI/Swagger "Authorize" button —
# the actual login endpoint lives on auth-service, not this app.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_db():
    return get_database()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> AuthenticatedUser:
    try:
        payload = await verify_access_token(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    subject = payload.get("sub")
    if subject is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    return AuthenticatedUser(id=subject, app_roles=payload.get("roles", {}))
