# Backend/api_v2/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes.health import router as health_router
from .api.routes.auth_routes import router as auth_router
from .api.routes.chat_routes import router as chat_router
from .api.routes.llm_models_routes import router as models_router
from .api.routes.folders_routes import router as folder_router
from .api.routes.user_routes import router as user_router

import logging
from contextlib import asynccontextmanager

from .config import get_settings
from .db.mongo import get_database
from .services.lightrag_service import initialize_lightrag

logger = logging.getLogger(__name__)


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

    # ---------- LIGHTRAG ----------
    try:
        await initialize_lightrag()
    except Exception:
        logger.exception(
            "LightRAG initialization failed – RAG queries will be unavailable."
        )

    yield  # App runs from here

    # SHUTDOWN (optional)
    # terminate Mongo connections here


def create_app() -> FastAPI:
    app = FastAPI(
        title="GDPR Chatbot Backend",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
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
    # User Router
    app.include_router(user_router, prefix="/api")

    return app

app = create_app()

@app.get("/debug-config")
def debug_config():
    settings = get_settings()
    return {
        "openrouter": bool(settings.openrouter_api_key),
        "key": settings.openrouter_api_key,
        "ollama_base_url": bool(settings.ollama_base_url),
        "mongo_url": settings.mongo_url,
        "mongo_db": settings.mongo_db_name
    }
