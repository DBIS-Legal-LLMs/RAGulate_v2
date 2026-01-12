# Backend/api_v2/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes.health import router as health_router
from .api.routes.auth import router as auth_router
from .api.routes.chat import router as chat_router
from .api.routes.llm_models import router as models_router
from .api.routes.folders import router as folder_router

from contextlib import asynccontextmanager

from .db.mongo import get_database

from .config import get_settings

def create_app() -> FastAPI:
    app = FastAPI(
        title="GDPR Chatbot Backend",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    origins = [
        "http://localhost:3000",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Hier sind die Router registriert

    # Check Health Router
    app.include_router(health_router, prefix="/api")
    # Authenticator Router
    app.include_router(auth_router, prefix="/api")
    # Chat Router
    app.include_router(chat_router, prefix="/api")
    # LLM Router
    app.include_router(models_router, prefix="/api")
    # Folder Router
    app.include_router(folder_router, prefix="/api")

    return app

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    db = get_database()

    # ---------- FOLDERS ----------
    await db["folders"].create_index(
        [("owner_id", 1), ("parent_id", 1), ("name", 1)],
        unique=True,
    )

    await db["folders"].create_index(
        [("owner_id", 1), ("parent_id", 1)]
    )

    # ---------- CHAT SESSIONS ----------
    await db["chat_sessions"].create_index(
        [("user_id", 1), ("folder_id", 1), ("updated_at", -1)]
    )

    # ---------- CHAT MESSAGES ----------
    await db["chat_messages"].create_index(
        [("session_id", 1), ("created_at", 1)]
    )

    yield  # App runs from here

    # SHUTDOWN (optional)
    # terminate Mongo connections here

app = create_app()

@app.get("/debug-config")
def debug_config():
    settings = get_settings()
    return {
        "openrouter": bool(settings.openrouter_api_key),
        "huggingface": bool(settings.huggingface_api_key),
        "ollama_base_url": bool(settings.ollama_base_url),
        "mongo_url": settings.mongo_url,
        "mongo_db": settings.mongo_db_name
    }
