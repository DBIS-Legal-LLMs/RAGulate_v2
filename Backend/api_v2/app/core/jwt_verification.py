# Backend/api_v2/app/core/jwt_verification.py

"""Verifies JWTs issued by auth-service against its published JWKS.

RAGulate no longer signs or stores credentials itself — this is pure,
stateless signature verification against a cached public key set.
"""

import time
from typing import Any

import httpx
from jose import jwt, JWTError

from ..config import get_settings

_jwks_cache: dict | None = None
_jwks_cache_time: float = 0.0
_CACHE_TTL_SECONDS = 300


async def _fetch_jwks() -> dict:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{settings.auth_service_url}/.well-known/jwks.json")
        resp.raise_for_status()
        return resp.json()


async def _get_jwks(force_refresh: bool = False) -> dict:
    global _jwks_cache, _jwks_cache_time
    now = time.monotonic()
    if force_refresh or _jwks_cache is None or (now - _jwks_cache_time) > _CACHE_TTL_SECONDS:
        _jwks_cache = await _fetch_jwks()
        _jwks_cache_time = now
    return _jwks_cache


async def verify_access_token(token: str) -> dict[str, Any]:
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as e:
        raise ValueError("Invalid token") from e

    kid = header.get("kid")
    jwks = await _get_jwks()
    key = next((k for k in jwks["keys"] if k.get("kid") == kid), None)

    if key is None:
        # Key not found — could be a rotated signing key we haven't seen yet.
        jwks = await _get_jwks(force_refresh=True)
        key = next((k for k in jwks["keys"] if k.get("kid") == kid), None)
        if key is None:
            raise ValueError("Unknown signing key")

    try:
        return jwt.decode(token, key, algorithms=["RS256"])
    except JWTError as e:
        raise ValueError("Invalid token") from e
