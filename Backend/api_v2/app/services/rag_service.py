# Backend/api_v2/app/services/rag_service.py

import os
import asyncio
import threading
from typing import Literal, Optional, Dict, List

import httpx
from transformers import AutoTokenizer, AutoModel
from huggingface_hub import InferenceClient
from openai import OpenAI

from lightrag import LightRAG, QueryParam
from lightrag.kg.shared_storage import initialize_pipeline_status
from lightrag.llm.hf import hf_embed
from lightrag.utils import EmbeddingFunc

from ..config import get_settings

settings = get_settings()

# ----------------------------------------------------------------------
# Provider-Typen & Model-Katalog
# ----------------------------------------------------------------------

LLMProviderName = Literal["huggingface", "openrouter", "ollama"]

# Hier definierst du, welche Modelle pro Provider zur Verfügung stehen.
# Werte sind die *internen* IDs, die dann direkt an die APIs gehen.
SUPPORTED_MODELS: Dict[LLMProviderName, List[str]] = {
    "huggingface": [
        # HF Inference-API Modellnamen
        # -> diese Modelle laufen auf der Hugging Face Inference API
        "mistralai/Mistral-7B-Instruct-v0.2",
        # hier kannst du weitere ergänzen
    ],
    "openrouter": [
        # OpenRouter Modell-IDs, Beispiel:
        "openai/gpt-4o-mini",
        "meta-llama/llama-3.1-8b-instruct",
        # weitere Modelle nach Geschmack
    ],
    "ollama": [
        # Lokale Ollama-Modelle
        "llama3:8b",
        "mistral:7b",
        # weitere, wenn du sie in Ollama geladen hast
    ],
}

# Default-Modell pro Provider (falls User nichts gewählt hat)
DEFAULT_MODEL: Dict[LLMProviderName, str] = {
    provider: models[0] for provider, models in SUPPORTED_MODELS.items()
}

# ----------------------------------------------------------------------
# LightRAG-Workspace + Embeddings
# ----------------------------------------------------------------------

DEFAULT_WORKDIR = "/app/Data/lightrag_storage"
WORKING_DIR = os.getenv("RAG_WORKDIR", DEFAULT_WORKDIR)
os.makedirs(WORKING_DIR, exist_ok=True)

_EMB_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_emb_tokenizer = None
_emb_model = None
_emb_lock = threading.Lock()


def _get_embedding_models():
    """Lazy-Laden von Tokenizer & Model für Embeddings."""
    global _emb_tokenizer, _emb_model
    if _emb_tokenizer is not None and _emb_model is not None:
        return _emb_tokenizer, _emb_model

    with _emb_lock:
        if _emb_tokenizer is None or _emb_model is None:
            _emb_tokenizer = AutoTokenizer.from_pretrained(_EMB_MODEL_NAME)
            _emb_model = AutoModel.from_pretrained(_EMB_MODEL_NAME)
        return _emb_tokenizer, _emb_model


async def _embedding_func(texts: List[str]):
    """Async-Wrapper um hf_embed, damit wir es in LightRAG nutzen können."""
    tokenizer, model = _get_embedding_models()
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        lambda: hf_embed(texts, tokenizer=tokenizer, embed_model=model),
    )


EMBEDDING_WRAPPER = EmbeddingFunc(
    embedding_dim=384,
    max_token_size=5000,
    func=_embedding_func,
)

# ----------------------------------------------------------------------
# Provider-Clients
# ----------------------------------------------------------------------

_openrouter_client: Optional[OpenAI] = None
_hf_clients: Dict[str, InferenceClient] = {}  # pro Modell ein Client
_hf_lock = threading.Lock()


def _get_openrouter_client() -> OpenAI:
    global _openrouter_client
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY ist nicht gesetzt.")
    if _openrouter_client is None:
        _openrouter_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
        )
    return _openrouter_client


def _get_hf_client(model_id: str) -> InferenceClient:
    if not settings.huggingface_api_key:
        raise RuntimeError("HUGGINGFACE_API_KEY ist nicht gesetzt.")
    with _hf_lock:
        if model_id not in _hf_clients:
            _hf_clients[model_id] = InferenceClient(
                model=model_id,
                token=settings.huggingface_api_key,
            )
        return _hf_clients[model_id]


# ----------------------------------------------------------------------
# Provider-spezifische Generate-Funktionen
# ----------------------------------------------------------------------

async def _generate_openrouter(
    model: str,
    messages: List[Dict[str, str]],
    max_tokens: int = 512,
    **kwargs,
) -> str:
    client = _get_openrouter_client()
    loop = asyncio.get_running_loop()
    resp = await loop.run_in_executor(
        None,
        lambda: client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            **kwargs,
        ),
    )
    return resp.choices[0].message.content


async def _generate_huggingface(
    model: str,
    messages: List[Dict[str, str]],
    max_new_tokens: int = 512,
    **kwargs,
) -> str:
    # Wir nehmen einfach die letzte User-Nachricht + optional System & History
    # und geben sie als Text-Generation Prompt an HF weiter.
    # Du kannst das bei Bedarf komplexer machen.
    prompt_parts = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "system":
            prompt_parts.append(f"[System] {content}\n")
        elif role == "assistant":
            prompt_parts.append(f"[Assistant] {content}\n")
        else:
            prompt_parts.append(f"[User] {content}\n")
    prompt = "\n".join(prompt_parts) + "\n[Assistant] "

    client = _get_hf_client(model)
    loop = asyncio.get_running_loop()
    resp = await loop.run_in_executor(
        None,
        lambda: client.text_generation(
            prompt,
            max_new_tokens=max_new_tokens,
            **kwargs,
        ),
    )
    # HF-Response ist einfach ein String (kompletter Text)
    # Wir wollen nur den generierten Teil nach dem Prompt
    # (ganz grob, du kannst das später feiner machen).
    if isinstance(resp, str) and resp.startswith(prompt):
        return resp[len(prompt):].strip()
    return resp.strip() if isinstance(resp, str) else str(resp)


async def _generate_ollama(
    model: str,
    messages: List[Dict[str, str]],
    **kwargs,
) -> str:
    """
    Nutzt die Ollama /api/chat-API.
    Erwartet, dass Ollama unter settings.ollama_base_url läuft.
    """
    base_url = settings.ollama_base_url or "http://localhost:11434"
    url = f"{base_url.rstrip('/')}/api/chat"

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        # Format laut Ollama-Doku: data["message"]["content"]
        msg = data.get("message", {}) or {}
        content = msg.get("content")
        if content:
            return content.strip()
        return str(data)

# ----------------------------------------------------------------------
# Multiplex-LLM-Wrapper (wird an LightRAG übergeben)
# ----------------------------------------------------------------------

async def _llm_model_func(
    prompt: str,
    system_prompt: Optional[str] = None,
    history_messages: Optional[List[Dict[str, str]]] = None,
    llm_provider: LLMProviderName = "openrouter",
    llm_model: Optional[str] = None,
    **kwargs,
) -> str:
    """
    Diese Funktion wird von LightRAG aufgerufen.
    Über llm_provider & llm_model (aus **kwargs) wählen wir zur Laufzeit:
      - welchen Provider (HF/OpenRouter/Ollama)
      - welches Modell
    """
    provider: LLMProviderName = llm_provider
    model_id = llm_model or DEFAULT_MODEL[provider]

    # Chat-Nachrichten zusammenbauen (system + history + aktueller Prompt)
    messages: List[Dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    if history_messages:
        messages.extend(history_messages)
    messages.append({"role": "user", "content": prompt})

    if provider == "openrouter":
        return await _generate_openrouter(model=model_id, messages=messages, **kwargs)
    elif provider == "huggingface":
        return await _generate_huggingface(model=model_id, messages=messages, **kwargs)
    elif provider == "ollama":
        return await _generate_ollama(model=model_id, messages=messages, **kwargs)
    else:
        raise ValueError(f"Unsupported provider: {provider}")

# ----------------------------------------------------------------------
# LightRAG-Instanz (einmalig)
# ----------------------------------------------------------------------

_rag_instance: Optional[LightRAG] = None
_rag_lock = asyncio.Lock()


async def get_rag() -> LightRAG:
    """
    Liefert eine initialisierte LightRAG-Instanz.
    Wir benutzen EIN RAG mit einem dynamischen llm_model_func, der
    pro Anfrage den Provider/Model aus kwargs wählt.
    """
    global _rag_instance
    if _rag_instance is not None:
        return _rag_instance

    async with _rag_lock:
        if _rag_instance is not None:
            return _rag_instance

        rag = LightRAG(
            working_dir=WORKING_DIR,
            llm_model_func=_llm_model_func,
            embedding_func=EMBEDDING_WRAPPER,
        )

        await rag.initialize_storages()
        await initialize_pipeline_status()

        _rag_instance = rag
        return rag

# ----------------------------------------------------------------------
# High-Level Helper: run_rag_query
# ----------------------------------------------------------------------

async def run_rag_query(
    question: str,
    *,
    provider: LLMProviderName = "openrouter",
    model: Optional[str] = None,
    mode: Literal["local", "global", "hybrid", "naive", "mix"] = "hybrid",
    response_type: str = "Multiple Paragraphs",
    user_prompt: str | None = None,
    history_messages: Optional[List[Dict[str, str]]] = None,
) -> str:
    """
    Führt eine LightRAG-Query aus und gibt nur den Antwort-String zurück.
    provider + model bestimmen, welcher LLM benutzt wird.
    """
    rag = await get_rag()

    if model is None:
        model = DEFAULT_MODEL[provider]

    param = QueryParam(
        mode=mode,
        response_type=response_type,
        user_prompt=user_prompt,
    )

    result = await rag.aquery(
        question,
        param=param,
        history_messages=history_messages or [],
        llm_provider=provider,
        llm_model=model,
    )

    # LightRAG gibt meist ein Dict mit 'response' zurück
    if isinstance(result, dict) and "response" in result:
        return result["response"]
    return str(result)


def get_supported_models() -> Dict[LLMProviderName, List[str]]:
    """
    Kannst du später in einem Endpoint verwenden, um dem Frontend mitzuteilen,
    welche Provider/Modelle zur Auswahl stehen.
    """
    return SUPPORTED_MODELS
