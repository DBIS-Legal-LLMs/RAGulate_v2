"""
Schemas for the Ragas evaluation API.

The backend POSTs a list of (query, retrieved contexts, generated response)
triples — one per BPMN element/critical-element — and the service returns
per-sample Ragas scores plus aggregate means.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class RagasSample(BaseModel):
    """A single (query, contexts, response) triple to score."""
    id: str = Field(..., description="Caller-supplied identifier (e.g. BPMN element id).")
    query: str = Field(..., min_length=1, description="The user/system question that drove retrieval.")
    contexts: list[str] = Field(
        default_factory=list,
        description="Retrieved context chunks that were given to the LLM.",
    )
    response: str = Field(
        ...,
        description="The LLM-generated answer/explanation grounded in the contexts.",
    )


class RagasEvaluationRequest(BaseModel):
    samples: list[RagasSample] = Field(..., min_length=1)
    metrics: Optional[list[str]] = Field(
        default=None,
        description=(
            "Subset of metric names to run. Supported: "
            "'faithfulness', 'context_utilization'. Defaults to all if omitted."
        ),
    )


class RagasSampleResult(BaseModel):
    id: str
    faithfulness: Optional[float] = None
    context_utilization: Optional[float] = None
    error: Optional[str] = None


class RagasAggregate(BaseModel):
    faithfulness_mean: Optional[float] = None
    context_utilization_mean: Optional[float] = None
    sample_count: int = 0
    failed_count: int = 0


class RagasEvaluationResponse(BaseModel):
    samples: list[RagasSampleResult]
    aggregate: RagasAggregate
    status: str = "success"
