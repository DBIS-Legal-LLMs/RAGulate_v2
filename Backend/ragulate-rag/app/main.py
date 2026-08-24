"""
ragulate-rag FastAPI application entry point.

Copied from GRIPL-v2's gripl-rag (same pipeline, own Neo4j and document
corpus) — see RAGulate_v2 issue #124 for why this isn't a shared instance.

Run with:
    uvicorn app.main:app --reload --port 8081
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as rag_router
from app.api.evaluation_routes import router as evaluation_router
from app.api.pdf_routes import router as pdf_router

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
# TODO: Disable docs in production (e.g., FastAPI(docs_url=None)) later
app = FastAPI(
    title="ragulate-rag",
    description=(
        "Retrieval-Augmented Generation API for RAGulate. "
        "Queries a LightRAG knowledge graph (seeded with GDPR regulation + "
        "EDPB guidance as a starting corpus) and returns relevant context."
    ),
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    # TODO: Change this to only allow the frontend and backend origins later
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Register routers
# ---------------------------------------------------------------------------
app.include_router(rag_router)
app.include_router(evaluation_router)
app.include_router(pdf_router)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint – redirects to the docs."""
    return {
        "service": "ragulate-rag",
        "docs": app.docs_url,
        "health": "/api/health",
    }
