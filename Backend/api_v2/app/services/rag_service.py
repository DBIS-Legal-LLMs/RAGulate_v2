# Backend/api_v2/app/services/rag_service.py
#
# Retrieves context from ragulate-rag (RAGulate's own RAG pipeline — see
# Backend/ragulate-rag/, copied from GRIPL's gripl-rag, own Neo4j/corpus)
# and injects it into the LLM call this service already makes.
#
# Retrieval is single-turn: only the latest user message is sent as the
# query. LightRAG has no multi-turn concept, and this codebase previously
# stalled on exactly that mismatch (see Common/General meeting notes,
# 2026-03-24) — the full conversation history still goes to the actual
# answer-generating LLM call below, unchanged.

import logging
from typing import AsyncGenerator, Dict, List, Optional

import httpx

from .llm_service import stream_chat_response
from ..config import get_settings

logger = logging.getLogger(__name__)


async def _fetch_context(question: str) -> Optional[dict]:
    """Queries ragulate-rag. Returns None (not an exception) on any failure
    so chat degrades gracefully to plain LLM output instead of erroring."""
    settings = get_settings()
    if not settings.ragulate_rag_url:
        return None

    try:
        async with httpx.AsyncClient(timeout=settings.ragulate_rag_timeout) as client:
            resp = await client.post(
                f"{settings.ragulate_rag_url}/api/query",
                json={"query": question, "mode": "hybrid"},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        logger.warning("ragulate-rag query failed, falling back to plain chat", exc_info=True)
        return None

    if data.get("status") != "success":
        return None
    return data.get("response")


def _format_context(parsed: dict) -> Optional[str]:
    documents = parsed.get("documents") or []
    if not documents:
        return None

    parts = ["Relevant context retrieved from the knowledge base:"]
    for doc in documents:
        source = doc.get("source_document") or "unknown source"
        content = (doc.get("content") or "").strip()
        if content:
            parts.append(f"\n[Source: {source}]\n{content}")

    if len(parts) == 1:
        return None

    parts.append(
        "\nUse the context above to answer the user's question where relevant. "
        "If it doesn't contain the answer, say so rather than guessing."
    )
    return "\n".join(parts)


async def run_rag_query(
    *,
    question: str,
    history_messages: Optional[List[Dict[str, str]]] = None,
    system_prompt: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    Build the message list and call the LLM.

    `history_messages` must already include the current user turn as its last
    entry (chat_service adds it before calling here).
    """
    messages: List[Dict[str, str]] = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    parsed_context = await _fetch_context(question)
    if parsed_context:
        context_text = _format_context(parsed_context)
        if context_text:
            messages.append({"role": "system", "content": context_text})

    if history_messages:
        messages.extend(history_messages)

    async for chunk in stream_chat_response(messages):
        yield chunk
