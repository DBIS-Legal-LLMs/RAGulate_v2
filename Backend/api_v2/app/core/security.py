# Backend/api_v2/app/core/security.py

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

from ..config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_settings = get_settings()

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)

def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    if expires_delta is None:
        expires_delta = timedelta(
            minutes=_settings.jwt_access_token_expire_minutes
        )

    payload: dict[str, Any] = {
        "sub": subject,
        "exp": datetime.now(timezone.utc) + expires_delta,
    }
    if extra_claims:
        payload.update(extra_claims)

    token = jwt.encode(
        payload,
        _settings.jwt_secret,
        algorithm=_settings.jwt_algorithm,
    )
    return token

def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            _settings.jwt_secret,
            algorithms=[_settings.jwt_algorithm],
        )
        return payload
    except JWTError as e:
        raise ValueError("Invalid token") from e
