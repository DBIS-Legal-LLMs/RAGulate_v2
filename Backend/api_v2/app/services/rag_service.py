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
import networkx as nx

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
    tokenizer, model = _get_embedding_models()
    
    def _embed():
        import torch
        inputs = tokenizer(texts, padding=True, truncation=True, return_tensors="pt", max_length=512)
        with torch.no_grad():
            outputs = model(**inputs)
        embeddings = outputs.last_hidden_state.mean(dim=1)
        return embeddings.cpu().numpy()
    
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _embed)


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
            torch_dtype= torch.float16 if torch.cuda.is_available() else torch.float32,
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
        tokenize= True,
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
# LightRAG-Cache pro (provider,model)
# Multiplex-LLM-Wrapper (wird an LightRAG übergeben)
# ----------------------------------------------------------------------

_rag_instances: Dict[tuple[str, str], LightRAG] = {}
_rag_lock = asyncio.Lock()

async def get_rag(provider: LLMProviderName, model_id: str) -> LightRAG:
    key = (provider, model_id)
    if key in _rag_instances:
        return _rag_instances[key]

    async with _rag_lock:
        if key in _rag_instances:
            return _rag_instances[key]

        # llm_model_func schließt Provider/Modell ein
        async def llm_func(prompt: str, system_prompt=None, history_messages=None, **kwargs):
            msgs = []
            if system_prompt:
                msgs.append({"role": "system", "content": system_prompt})
            if history_messages:
                msgs.extend(history_messages)
            msgs.append({"role": "user", "content": prompt})

            if provider == "openrouter":
                return await _generate_openrouter(model=model_id, messages=msgs, **kwargs)
            elif provider == "huggingface":
                return await _generate_huggingface(model=model_id, messages=msgs, **kwargs)
            elif provider == "ollama":
                return await _generate_ollama(model=model_id, messages=msgs, **kwargs)
            else:
                raise ValueError(f"Unsupported provider: {provider}")

        rag = LightRAG(
            working_dir=WORKING_DIR,
            llm_model_func=llm_func,
            embedding_func=EMBEDDING_WRAPPER,
        )
        await rag.initialize_storages()
        await initialize_pipeline_status()

        _rag_instances[key] = rag
        return rag
    

# ----------------------------------------------------------------------
# History Builder
# ----------------------------------------------------------------------

def _render_history_to_system(history_messages: list[dict] | None) -> str:
    if not history_messages:
        return ""
    lines = []
    for m in history_messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        lines.append(f"{role.upper()}: {content}")
    return "Chat history (for context):\n" + "\n".join(lines)


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
    model_id = model or DEFAULT_MODEL[provider]
    rag = await get_rag(provider=provider, model_id=model_id)

    # History -> system_prompt mappen
    hist_block = _render_history_to_system(history_messages=history_messages)
    system_prompt = "\n\n".join([p for p in [user_prompt, hist_block] if p])

    param = QueryParam(
        mode=mode,
        response_type=response_type,
        user_prompt=None,
    )

    result = await rag.aquery(
        question,
        param=param,
        system_prompt=system_prompt or None,
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

def get_graph_data() -> dict:
    graph_path = os.path.join(WORKING_DIR, "graph_chunk_entity_relation.graphml")

    if not os.path.exists(graph_path):
        return {"nodes": [], "edges": [], "node_count": 0, "edge_count": 0}

    G = nx.read_graphml(graph_path)

    nodes = [
        {
            "id": node_id,
            "label": data.get("entity_name", node_id),
            "type": data.get("entity_type", "UNKNOWN"),
            "description": data.get("description", ""),
        }
        for node_id, data in G.nodes(data=True)
    ]

    edges = [
        {
            "id": f"{u}-{v}",
            "source": u,
            "target": v,
            "label": data.get("keywords", ""),
            "weight": float(data.get("weight", 1.0)),
            "description": data.get("description", ""),
        }
        for u, v, data in G.edges(data=True)
    ]

    return {"nodes": nodes, "edges": edges, "node_count": len(nodes), "edge_count": len(edges)}
