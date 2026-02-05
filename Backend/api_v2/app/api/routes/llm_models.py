# Backend/api_v2/app/api/routes/llm_models.py

from typing import Dict

from fastapi import APIRouter
from pydantic import BaseModel

from ...config import get_settings
from ...services.rag_service import (
    get_supported_models,
    DEFAULT_MODEL,
    LLMProviderName,
)

settings = get_settings()
router = APIRouter(prefix="/models", tags=["models"])

class ProviderInfo(BaseModel):
    default: str
    models: list[str]

class ModelsResponse(BaseModel):
    providers: Dict[LLMProviderName, ProviderInfo]


@router.get("", response_model=ModelsResponse)
async def list_models() -> ModelsResponse:
    """
    Liefert alle verfügbaren LLM-Provider & deren unterstützte Modelle zurück.

    - Filtert Provider ohne gesetzte API-Keys raus (openrouter, huggingface)
    - Ollama bleibt immer sichbar (läuft lokal)
    """

    supported = get_supported_models()

    providers: Dict[LLMProviderName, ProviderInfo] = {}

    for provider, models in supported.items():
        # Provider filtern, wenn nicht konfiguriert
        if provider == "openrouter" and not settings.openrouter_api_key:
            continue
        if provider == "huggingface" and not settings.huggingface_api_key:
            continue
        # Ollama: kein Key nötig -> immer anzeigen

        providers[provider] = ProviderInfo(
            default= DEFAULT_MODEL[provider],
            models= models,
        )

    return ModelsResponse(providers= providers)