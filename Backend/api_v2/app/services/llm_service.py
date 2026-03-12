
# Backend/api_v2/app/services/llm_service.py
 
from __future__ import annotations
 
from typing import Dict, List, Literal
 
import httpx
 
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

async def _generate_openrouter(messages: List[Dict[str, str]]) -> str:
    """
    Calls OpenRouter's OpenAI-compatible /chat/completions endpoint
    directly via httpx — no extra SDK required.
    """
    url = f"{settings.openrouter_base_url.rstrip('/')}/chat/completions"
 
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
    }
 
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
    }
 
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
 
    return data["choices"][0]["message"]["content"].strip()


# ---------------------------------------------------------------------------
# Internal: Ollama (local)
# ---------------------------------------------------------------------------

async def _generate_ollama(messages: List[Dict[str, str]]) -> str:
    """
    Calls the local Ollama REST API.
    The model must already be pulled on the host machine:
        ollama pull qwen2.5:4b
    """
    url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"
 
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }
 
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
 
    return data["message"]["content"].strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
 
async def generate_chat_response(messages: List[Dict[str, str]]) -> str:
    """
    Single entry point for all LLM calls.
 
    Resolution order:
      1. OpenRouter  — when OPENROUTER_API_KEY is set.
      2. Ollama      — when the key is missing OR OpenRouter raises any error.
    """
    if settings.openrouter_api_key:
        try:
            return await _generate_openrouter(messages)
        except Exception as exc:
            print(f"[llm_service] OpenRouter failed ({exc!r}), falling back to Ollama.")
 
    return await _generate_ollama(messages)
 
 
def get_active_provider() -> LLMProviderName:
    """Indicates which provider will handle the next request."""
    return "openrouter" if settings.openrouter_api_key else "ollama"