from fastapi import APIRouter, HTTPException
from ..services.rag_service import get_graph_data

router = APIRouter(prefix="/graph", tags=["graph"])

@router.get("/")
def graph_endpoint():
    try:
        return get_graph_data()
    except Exception as e:
        raise HTTPException(500, str(e))