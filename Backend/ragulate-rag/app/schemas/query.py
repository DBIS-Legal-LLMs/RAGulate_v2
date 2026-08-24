"""
Request and response schemas for the RAG query API.
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from enum import Enum
from typing import Any


class QueryMode(str, Enum):
    """LightRAG search modes."""
    naive = "naive"
    local = "local"
    global_ = "global"
    hybrid = "hybrid"


class QueryRequest(BaseModel):
    query: str = Field(
        ...,
        description="The query text to search for in the knowledge graph.",
        min_length=1,
        max_length=10000,
    )
    mode: QueryMode = Field(
        default=QueryMode.hybrid,
        description="LightRAG search mode: naive, local, global, or hybrid.",
    )


class RagEntity(BaseModel):
    id: str
    label: str
    type: str
    description: list[str]
    description_text: str


class RagRelationship(BaseModel):
    source: str
    source_label: str
    target: str
    target_label: str
    label: str


class RagDocument(BaseModel):
    id: str
    source_document: str | None
    content: str
    preview: str


class RagMeta(BaseModel):
    entity_count: int
    relationship_count: int
    document_count: int


class ParsedRagResponse(BaseModel):
    """Structured output from the RAG parser."""
    entities: list[RagEntity]
    relationships: list[RagRelationship]
    documents: list[RagDocument]
    meta: RagMeta


class QueryResponse(BaseModel):
    query: str = Field(
        ...,
        description="The original query that was sent.",
    )
    mode: str = Field(
        ...,
        description="The search mode that was used.",
    )
    response: ParsedRagResponse = Field(
        ...,
        description="Parsed context with entities, relationships, and documents.",
    )
    status: str = Field(
        default="success",
        description="Status of the query: 'success' or 'error'.",
    )


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    service: str = "ragulate-rag"
