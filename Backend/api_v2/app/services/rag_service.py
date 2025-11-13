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

from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

settings = get_settings()

# ----------------------------------------------------------------------
# Provider-Typen & Model-Katalog
# ----------------------------------------------------------------------

LLMProviderName = Literal["huggingface", "openrouter", "ollama"]

# Hier definierst du, welche Modelle pro Provider zur Verfügung stehen.
# Werte sind die *internen* IDs, die dann direkt an die APIs gehen.
# Das erstgenannte Model pro Provider ist der Default
SUPPORTED_MODELS: Dict[LLMProviderName, List[str]] = {
    "huggingface": [
        # HF Inference-API Modellnamen
        # -> diese Modelle laufen auf der Hugging Face Inference API
        "mistralai/Mistral-7B-Instruct-v0.2",
        # hier kannst du weitere ergänzen
    ],
    "openrouter": [
        # OpenRouter Modell-IDs, Beispiel:
        "mistralai/mistral-nemo",
        # weitere Modelle nach Geschmack
    ],
    "ollama": [
        # Lokale Ollama-Modelle
        "gwen3:8b",
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
            base_url=settings.openrouter_base_url,
            api_key=settings.openrouter_api_key,
        )
    return _openrouter_client


_hf_local_models: Dict[str, Dict[str, object]] = {} # Cache pro Model
_hf_local_lock = threading.Lock()


def _load_hf_model(model_id: str):
    """
    Lädt Tokenizer & Modell lokal (Transformers/PyTorch).
    Wird gecacht, um wiederholtes Laden zu vermeiden.
    """
    with _hf_local_lock:
        if model_id in _hf_local_models:
            return _hf_local_models[model_id]
        
        print(f"[LightRAG] Lade lokales HF-Modell: {model_id} ...")
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype= torch.float16 if torch.coda.is_available() else torch.float32,
            device_map= "auto",
        )
        _hf_local_models[model_id] = {"tokenizer": tokenizer, "model": model}
        return _hf_local_models[model_id]


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
    """
    Führt eine lokale Textgenerierung mit Transformers durch.
    """
    model_bundle = _load_hf_model(model)
    tokenizer = model_bundle["tokenizer"]
    model_obj = model_bundle["model"]

    # Nachrichten ins Chat-Template einbetten
    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt= True,
        tokenizer= True,
        return_dict= True,
        return_tensors= "pt",
    ).to(model_obj.device)

    # Text generieren
    with torch.no_grad():
        outputs = model_obj.generate(**inputs, max_new_tokens=max_new_tokens)

    # Nur den generierten Teil dekodieren
    output_text = tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True
    )

    return output_text.strip()


async def _generate_ollama(
    model: str,
    messages: List[Dict[str, str]],
    **kwargs,
) -> str:
    """
    Nutzt die Ollama /api/chat-API.
    Erwartet, dass Ollama unter settings.ollama_base_url läuft.
    """
    base_url = settings.ollama_base_url
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
    llm_provider: LLMProviderName = "huggingface",
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
    provider: LLMProviderName = "huggingface",
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
