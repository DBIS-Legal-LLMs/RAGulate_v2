# Backend/api_v2/app/api/routes/llm_models.py
 
from fastapi import APIRouter
from pydantic import BaseModel
 
from ...services.llm_service import (
    get_active_provider,
    get_active_model,
)
 
router = APIRouter(prefix="/models", tags=["models"])
 
 
class ModelsResponse(BaseModel):
    active_provider: str
    openrouter_model: str
    ollama_model: str
 
 
@router.get("", response_model=ModelsResponse)
async def list_models() -> ModelsResponse:
    """
    Returns the currently active provider and the configured model names
    for both providers.
    """
    return ModelsResponse(
        active_provider=get_active_provider(),
        openrouter_model=get_active_model(),
    )