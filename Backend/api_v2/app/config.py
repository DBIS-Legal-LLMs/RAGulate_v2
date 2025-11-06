# Backend/api_v2/app/config.py

from pydantic import BaseModel
from functools import lru_cache
import os

class Settings(BaseModel):
    env: str = os.getenv("APP_ENV")
    mongo_url: str = os.getenv("MONGO_URL")
    mongo_db_name: str = os.getenv("MONGO_DB_NAME")

    jwt_secret: str = os.getenv("JWT_SECRET")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES"))

    # LLM Provider Settings
    openrouter_api_key: str | None = os.getenv("OPENROUTER_API_KEY")
    openrouter_base_url: str | None = os.getenv("OPENROUTER_BASE_URL")

    huggingface_api_key: str | None = os.getenv("HF_API_KEY")
    
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL")



@lru_cache
def get_settings() -> Settings:
    return Settings()