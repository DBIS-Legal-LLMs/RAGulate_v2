# Backend/api_v2/app/services/lightrag_service.py
#
# Initializes a LightRAG instance backed by OpenRouter for both
# LLM completions and embeddings.  Documents placed in
# app/data/documents/ are ingested at server startup.

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import AsyncGenerator

from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc

from ..config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

DOCUMENTS_DIR = Path(__file__).parent.parent / "data" / "documents"

# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_rag_instance: LightRAG | None = None


def get_rag() -> LightRAG:
    if _rag_instance is None:
        raise RuntimeError(
            "LightRAG has not been initialized. "
            "Ensure initialize_lightrag() is awaited at server startup."
        )
    return _rag_instance


# ---------------------------------------------------------------------------
# LLM and embedding functions wired to OpenRouter
# ---------------------------------------------------------------------------

async def _llm_model_func(
    prompt: str,
    system_prompt: str | None = None,
    history_messages: list | None = None,
    **kwargs,
) -> str:
    return await openai_complete_if_cache(
        model=settings.openrouter_model,
        prompt=prompt,
        system_prompt=system_prompt,
        history_messages=history_messages or [],
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        **kwargs,
    )


async def _embedding_func(texts: list[str]) -> list[list[float]]:
    return await openai_embed(
        texts,
        model=settings.openrouter_embeddings_model,
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
    )


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

async def initialize_lightrag() -> None:
    """
    Called once at server startup.

    1. Creates the LightRAG instance (backed by OpenRouter).
    2. Initializes its storage backends.
    3. Ingests every file found in app/data/documents/.
       LightRAG skips documents it has already processed.
    """
    global _rag_instance

    working_dir = settings.lightrag_working_dir
    os.makedirs(working_dir, exist_ok=True)

    _rag_instance = LightRAG(
        working_dir=working_dir,
        llm_model_func=_llm_model_func,
        embedding_func=EmbeddingFunc(
            embedding_dim=settings.lightrag_embedding_dim,
            max_token_size=8192,
            func=_embedding_func,
        ),
    )

    await _rag_instance.initialize_storages()

    # Ingest documents
    if DOCUMENTS_DIR.exists():
        doc_files = [
            p for p in DOCUMENTS_DIR.iterdir()
            if p.is_file() and not p.name.startswith(".")
        ]
        if doc_files:
            for doc_path in doc_files:
                logger.info("Loading document for RAG: %s", doc_path.name)
                try:
                    text = doc_path.read_text(encoding="utf-8", errors="replace")
                    if text.strip():
                        await _rag_instance.ainsert(text)
                        logger.info("Inserted document into RAG: %s", doc_path.name)
                    else:
                        logger.warning("Document is empty, skipping: %s", doc_path.name)
                except Exception:
                    logger.exception("Failed to insert document: %s", doc_path.name)
        else:
            logger.info("No documents found in %s – LightRAG ready but empty.", DOCUMENTS_DIR)
    else:
        logger.warning("Documents directory not found: %s", DOCUMENTS_DIR)

    logger.info("LightRAG initialized successfully (working_dir=%s).", working_dir)


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

async def query_with_lightrag(
    question: str,
    mode: str | None = None,
) -> AsyncGenerator[str, None]:
    """
    Queries LightRAG and yields the response as a stream.

    LightRAG handles retrieval *and* the final LLM call internally.
    The full answer is yielded as a single chunk so the SSE generator
    in chat_service sees a compatible stream.
    """
    rag = get_rag()
    rag_mode = mode or settings.lightrag_rag_mode

    response = await rag.aquery(
        question,
        param=QueryParam(mode=rag_mode),
    )

    if response:
        yield str(response)
