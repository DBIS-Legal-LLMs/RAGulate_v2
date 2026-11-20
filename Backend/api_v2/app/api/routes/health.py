# Backend/api_v2/app/api/routes/health.py

import os

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])

@router.get("")
async def health_check():
    return {"status": "ok", "service": "gdpr-backend-v2", "version": os.getenv("APP_VERSION", "local")}