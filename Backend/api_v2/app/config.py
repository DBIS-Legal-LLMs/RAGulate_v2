# Backend/api_v2/app/config.py

from pydantic import BaseModel
from functools import lru_cache
import os

class Settings(BaseModel):
    env: str = os.getenv("APP_ENV", "local")
    mongo_url: str = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    mongo_db_name: str = os.getenv("MONGO_DB_NAME", "gdpr_chatbot")

    jwt_secret: str = os.getenv("JWT_SECRET")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_access_token_expire_minutes: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    # LLM Provider Settings
    openrouter_api_key: str | None = os.getenv("OPENROUTER_API_KEY")
    openrouter_baseurl: str | None = os.getenv("OPENROUTER_BASEURL", "https://openrouter.ai/api/v1")

    huggingface_api_key: str | None = os.getenv("HF_API_KEY")
    

    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


@lru_cache
def get_settings() -> Settings:
    return Settings()