# Backend/api_v2/app/core/security.py

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

import re

from email_validator import validate_email, EmailNotValidError

from ..config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_settings = get_settings()

# ----- E-Mail -----

def validate_email_address(email: str) -> str:
    try:
        v = validate_email(email, check_deliverability=True)
        return v.email
    except EmailNotValidError:
        raise ValueError("EMAIL_INVALID")


# ----- PASSWORDS -----

def validate_password_policy(password: str) -> list[str]:
    errors = []
    if len(password) < 8:
        errors.append("PASSWORD_TOO_SHORT")
    if not re.search(r"[A-Z]", password):
        errors.append("PASSWORD_NO_UPPERCASE")
    if not re.search(r"[a-z]", password):
        errors.append("PASSWORD_NO_LOWERCASE")
    if not re.search(r"[0-9]", password):
        errors.append("PASSWORD_NO_DIGIT")
    if not re.search(r"[!@#$%^&*()\-_=+{}\[\]|;:'\",.<>/?]", password):
        errors.append("PASSWORD_NO_SPECIAL")
    return errors

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)

# ----- ACCESS TOKEN -----

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
