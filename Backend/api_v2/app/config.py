# Backend/api_v2/app/config.py

from pydantic import BaseModel
from functools import lru_cache
import os

class Settings(BaseModel):
    env: str = os.getenv("APP_ENV")

    # MongoDB Settings
    mongo_url: str     = os.getenv("MONGO_URL")
    mongo_db_name: str = os.getenv("MONGO_DB_NAME")

    # auth-service (issues tokens, we only verify them against its JWKS)
    auth_service_url: str = os.getenv("AUTH_SERVICE_URL", "http://localhost:8100")

    # LLM Provider Settings
    openrouter_api_key: str | None   = os.getenv("OPENROUTER_API_KEY")
    openrouter_base_url: str         = os.getenv("OPENROUTER_BASE_URL")
    openrouter_model: str            = os.getenv("OPENROUTER_MODEL")
    openrouter_embeddings_model: str = os.getenv("OPENROUTER_EMBEDDINGS_MODEL")
    
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL")
    ollama_model: str    = os.getenv("OLLAMA_MODEL")

    # ragulate-rag (Backend/ragulate-rag/) — optional: chat still works
    # without it, just without retrieval, if unset or unreachable.
    ragulate_rag_url: str | None = os.getenv("RAGULATE_RAG_URL")
    ragulate_rag_timeout: float  = float(os.getenv("RAGULATE_RAG_TIMEOUT", "180"))


@lru_cache
def get_settings() -> Settings:
    return Settings()