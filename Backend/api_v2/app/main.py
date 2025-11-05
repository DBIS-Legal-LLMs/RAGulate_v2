# Backend/api_v2/app/main.py

from fastapi import FastAPI
from .api.routes.health import router as health_router
from .api.routes.auth import router as auth_router
from .api.routes.chat import router as chat_router

def create_app() -> FastAPI:
    app = FastAPI(
        title="GDPR Chatbot Backend",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Hier sind die Router registriert

    # Check Health Router
    app.include_router(health_router, prefix="/api")
    # Authenticator Router
    app.include_router(auth_router, prefix="/api")
    # Chat Router
    app.include_router(chat_router, prefix="/api")

    return app

app = create_app()