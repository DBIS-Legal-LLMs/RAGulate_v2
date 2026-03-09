# Backend/api_v2/app/services/llm_service.py

from __future__ import annotations

from typing import Dict, List, Literal, Optional

import httpx
from openai import OpenAI

from ..config import get_settings

settings = get_settings()

LLMProviderName = Literal["openrouter", "ollama"]

SUPPORTED_MODELS: Dict[str, List[str]] = {
    "openrouter": [
        # OpenRouter model id's
        "mistralai/mistral-small-3.1-24b-instruct:free",
    ],
    "ollama": [
        # local installed ollama models
        "qwen3.5:4b",
    ],
}

DEFAULT_MODEL: Dict[str, str] = {"openrouter": "mistralai/mistral-small-3.1-24b-instruct:free"}

_openrouter_client: Optional[OpenAI] = None


def _get_openrouter_client() -> OpenAI:
    global _openrouter_client

    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured.")

    if _openrouter_client is None:
        _openrouter_client = OpenAI(
            base_url=settings.openrouter_base_url,
            api_key=settings.openrouter_api_key,
        )

    return _openrouter_client


async def _generate_openrouter(
    model: str,
    messages: List[Dict[str, str]],
    max_tokens: int = 512,
) -> str:
    client = _get_openrouter_client()

    # OpenAI client ist sync -> in Thread ausführen
    import asyncio
    loop = asyncio.get_running_loop()

    response = await loop.run_in_executor(
        None,
        lambda: client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
        ),
    )

    content = response.choices[0].message.content
    return (content or "").strip()


async def _generate_ollama(
    model: str,
    messages: List[Dict[str, str]],
) -> str:
    if not settings.ollama_base_url:
        raise RuntimeError("OLLAMA_BASE_URL is not configured.")

    url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

    content = data.get("message", {}).get("content", "")
    return content.strip()


async def generate_chat_response(
    *,
    messages: List[Dict[str, str]],
    provider: LLMProviderName = "openrouter",
    model: Optional[str] = None,
    fallback_to_ollama: bool = True,
) -> str:
    provider_model = model or DEFAULT_MODEL[provider]

    try:
        if provider == "openrouter":
            return await _generate_openrouter(
                model=provider_model,
                messages=messages,
            )

        if provider == "ollama":
            return await _generate_ollama(
                model=provider_model,
                messages=messages,
            )

        raise ValueError(f"Unsupported provider: {provider}")

    except Exception:
        if provider == "openrouter" and fallback_to_ollama:
            return await _generate_ollama(
                model=DEFAULT_MODEL["ollama"],
                messages=messages,
            )
        raise


def get_supported_models() -> Dict[LLMProviderName, List[str]]:
    return SUPPORTED_MODELS