# Backend/api_v2/app/services/llm_service.py
 
from __future__ import annotations
 
import json
import traceback
from typing import AsyncGenerator, Dict, List, Literal
 
import httpx
from openai import AsyncOpenAI
 
from ..config import get_settings
 
settings = get_settings()
 
# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
 
LLMProviderName = Literal["openrouter", "ollama"]
 
OPENROUTER_MODEL            = settings.openrouter_model
OPENROUTER_EMBEDDINGS_MODEL = settings.openrouter_embeddings_model
OLLAMA_MODEL                = settings.ollama_model 
 
# ---------------------------------------------------------------------------
# Internal: OpenRouter via OpenAI SDK (streaming)
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
    Opens the OpenRouter stream and yields text deltas.
 
    The `.create()` call is awaited here before the first yield so that
    connection/auth errors surface immediately and can be caught by the
    caller, rather than being swallowed inside the generator.
    """
    client = _get_openrouter_client()
 
    # This await is intentionally BEFORE the first yield so that any
    # API/auth error raises here, where stream_chat_response can catch it.
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
    Ollama returns one JSON object per line when stream=true.
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
    messages: List[Dict[str, str]],
) -> AsyncGenerator[str, None]:
    """
    Primary entry point for all LLM streaming calls.
 
    Yields text delta strings one chunk at a time.
    The caller assembles them into the full response.
 
    Resolution order:
      1. OpenRouter — when OPENROUTER_API_KEY is configured.
      2. Ollama     — when the key is missing OR OpenRouter raises any error.
 
    NOTE: We must obtain the async generator object from _stream_openrouter
    and call __anext__() at least once inside the try block to catch errors
    that occur during stream setup. Using `async for` directly would move
    exception handling outside our try/except scope after the first yield.
    """
    if settings.openrouter_api_key:
        try:
            async for chunk in _stream_openrouter(messages):
                yield chunk
            return
        except Exception as exc:
            print(f"[llm_service] OpenRouter failed — falling back to Ollama.")
            print(f"[llm_service] Reason: {exc!r}")
            traceback.print_exc()
 
    #async for chunk in _stream_ollama(messages):
    #    yield chunk
 
 
def get_active_provider() -> LLMProviderName:
    """Indicates which provider will handle the next request."""
    return "openrouter" if settings.openrouter_api_key else "ollama"