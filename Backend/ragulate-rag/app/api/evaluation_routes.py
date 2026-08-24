"""
FastAPI router for Ragas-based RAG evaluation.

Exposes:
  POST /api/evaluate/ragas   evaluate a batch of (query, contexts, response) samples
"""
import logging
import asyncio

from fastapi import APIRouter, HTTPException

from app.schemas.evaluation import (
    RagasEvaluationRequest,
    RagasEvaluationResponse,
    RagasSampleResult,
    RagasAggregate,
)
from app.evaluation.ragas_evaluator import evaluate_samples

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/evaluate", tags=["Evaluation"])


@router.post("/ragas", response_model=RagasEvaluationResponse)
async def evaluate_ragas(request: RagasEvaluationRequest):
    logger.info(
        "Ragas evaluation request: %d sample(s), metrics=%s",
        len(request.samples),
        request.metrics or "all",
    )

    samples_payload = [
        {
            "id": s.id,
            "query": s.query,
            "contexts": s.contexts,
            "response": s.response,
        }
        for s in request.samples
    ]

    try:
        result = await asyncio.wait_for(
            evaluate_samples(samples_payload, requested_metrics=request.metrics),
            timeout=1800.0,
        )
    except asyncio.TimeoutError:
        logger.error("Ragas evaluation timed out")
        raise HTTPException(status_code=504, detail="Ragas evaluation timed out")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ragas evaluation failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Ragas evaluation failed: {exc}")

    return RagasEvaluationResponse(
        samples=[RagasSampleResult(**s) for s in result["samples"]],
        aggregate=RagasAggregate(**result["aggregate"]),
    )
