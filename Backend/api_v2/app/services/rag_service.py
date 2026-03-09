# Backend/api_v2/app/services/rag_service.py

from typing import Literal, Optional, Dict, List

import httpx
from openai import OpenAI

from ..config import get_settings


settings = get_settings()

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
        raise RuntimeError("OpenRouter api key is not set.")
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
        temperature: float = 0.7,
        **kwargs,
) -> str:
    client = _get_openrouter_client()
    import asyncio
    loop = asyncio.get_running_loop()

    response = await loop.run_in_executor(
        None,
        lambda: client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        ),
    )

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("OpenRouter returned empty content.")
    return content.strip()