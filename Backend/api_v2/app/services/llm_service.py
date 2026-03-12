
# Backend/api_v2/app/services/llm_service.py
 
from __future__ import annotations

import json
from typing import AsyncGenerator, Dict, List, Literal
 
import httpx
from openai import AsyncOpenAI
 
from ..config import get_settings
 
settings = get_settings()


# ---------------------------------------------------------------------------
# Constants — change model names here when needed
# ---------------------------------------------------------------------------

LLMProviderName = Literal["openrouter", "ollama"]
 
OPENROUTER_MODEL = "mistralai/ministral-3b-2512"
OPENROUTER_EMBEDDINGS_MODEL = "mistralai/mistral-embed-2312"
OLLAMA_MODEL     = "qwen2.5:4b"


# ---------------------------------------------------------------------------
# Internal: OpenRouter
# ---------------------------------------------------------------------------

_openrouter_client: AsyncOpenAI | None = None


def _get_openrouter_client() -> AsyncOpenAI:
    global _openrouter_client
    if _openrouter_client is None:
        _openrouter_client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )
    return _openrouter_client


async def _stream_openrouter(
        messages: List[Dict[str, str]],
) -> AsyncGenerator[str, None]:
    """
    Streams the OpenRouter response chunk by chunk via the OpenAI SDK.
    Yields each text delta as it arrives.
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


# ---------------------------------------------------------------------------
# Internal: Ollama (local, streaming)
# ---------------------------------------------------------------------------

async def _stream_ollama(
        messages: List[Dict[str, str]],
) -> AsyncGenerator[str, None]:
    """
    Streams the local Ollama response via httpx.
    Ollama returns one JSON object per line when stream=true;
    we extract the content delta from each line.
    """
    url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"

    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": True,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                data = json.loads(line)
                delta = data.get("message", {}).get("content", "")
                if delta:
                    yield delta


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
 
async def stream_chat_response(
        messages: List[Dict[ str, str]],
) -> AsyncGenerator[str, None]:
    """
    Primary entry point for all LLM streaming calls.
 
    Yields text delta strings one chunk at a time.
    The caller assembles them into the full response.
 
    Resolution order:
      1. OpenRouter — when OPENROUTER_API_KEY is configured.
      2. Ollama     — when the key is missing OR OpenRouter raises any error.
    """
    if settings.openrouter_api_key:
        try:
            async for chunk in _stream_openrouter(messages=messages):
                yield chunk
            return
        except Exception as exc:
            print(f"[llm_service] OpenRouter failed ({exc!r}), falling back to Ollama.")
    
    async for chunk in _stream_ollama(messages=messages):
        yield chunk
 
 
def get_active_provider() -> LLMProviderName:
    """Indicates which provider will handle the next request."""
    return "openrouter" if settings.openrouter_api_key else "ollama"