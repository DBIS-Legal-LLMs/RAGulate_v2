# Backend/api_v2/app/services/llm_service.py
 
from __future__ import annotations

from typing import AsyncGenerator, Dict, List, Literal

from openai import AsyncOpenAI
 
from ..config import get_settings
 
settings = get_settings()
 
# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
 
LLMProviderName = Literal["openrouter", "ollama"]
 
OPENROUTER_MODEL            = settings.openrouter_model
OPENROUTER_EMBEDDINGS_MODEL = settings.openrouter_embeddings_model
 
# ---------------------------------------------------------------------------
# Internal: OpenRouter via OpenAI SDK (streaming)
# ---------------------------------------------------------------------------
 
_openrouter_client: AsyncOpenAI | None = None
 
 
def _get_openrouter_client() -> AsyncOpenAI:
    global _openrouter_client
    if _openrouter_client is None:
        if settings.openrouter_api_key:
            _openrouter_client = AsyncOpenAI(
                api_key=settings.openrouter_api_key,
                base_url=settings.openrouter_base_url,
            )
        else:
            raise RuntimeError("OPENROUTER_API_KEY is not configured.")
    return _openrouter_client
 
# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
 
async def stream_chat_response(
    messages: List[Dict[str, str]],
) -> AsyncGenerator[str, None]:
    """
    Streams the OpenRouter response chunk by chunk via the OpenAI SDK.
    Yields text delta strings one at a time.
 
    Raises RuntimeError if OPENROUTER_API_KEY is not configured.
    Raises openai.APIError (or subclass) on API-level failures.
 
    The .create() call is awaited before the first yield so that
    connection/auth errors surface immediately and are catchable
    by the caller rather than being swallowed inside the generator.
    """
    client = _get_openrouter_client()

    stream = await client.chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=messages,
        stream=True,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
 
 
def get_active_provider() -> LLMProviderName:
    """Indicates which provider will handle the next request."""
    return "openrouter" if settings.openrouter_api_key else "no api key provided"