# Backend/api_v2/app/services/rag_service.py
#
# Retrieval-augmented generation using LightRAG.
# Falls back to a plain LLM call when LightRAG is unavailable.

import logging
from typing import AsyncGenerator, Dict, List, Optional

from .lightrag_service import get_rag, query_with_lightrag
from .llm_service import stream_chat_response

logger = logging.getLogger(__name__)


async def run_rag_query(
    *,
    question: str,
    history_messages: Optional[List[Dict[str, str]]] = None,
    system_prompt: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    Answer the user's question using LightRAG for retrieval.

    LightRAG handles both document retrieval and the final LLM call
    internally, so the question is forwarded directly to it.

    Falls back to a plain LLM call (with full conversation history)
    when LightRAG is not initialised or raises an error.
    """
    try:
        get_rag()  # raises RuntimeError if initialize_lightrag() was not called
        async for chunk in query_with_lightrag(question):
            yield chunk
        return
    except RuntimeError:
        logger.warning(
            "LightRAG is not initialized (check startup logs). "
            "Falling back to plain LLM without document retrieval."
        )
    except Exception:
        logger.exception(
            "LightRAG query failed, falling back to plain LLM."
        )

    # ---------- Fallback: plain LLM ----------
    messages: List[Dict[str, str]] = []

    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    if history_messages:
        messages.extend(history_messages)

    async for chunk in stream_chat_response(messages):
        yield chunk

 