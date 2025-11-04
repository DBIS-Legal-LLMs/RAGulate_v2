# Backend/api_v2/app/main.py

from fastapi import FastAPI
from .api.routes.health import router as health_router

def create_app() -> FastAPI:
    app = FastAPI(
        title="GDPR Chatbot Backend",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Router registrieren
    app.include_router(health_router)

    return app

app = create_app()