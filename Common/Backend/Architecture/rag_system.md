# RAG System

The Retrieval Augmented Generation (RAG) system enriches LLM prompts
with relevant contextual information retrieved from stored documents.

## Purpose

RAG improves answer quality by allowing the LLM to reference external
knowledge (currently: GDPR regulation text + EDPB guidance) instead of
relying only on the model's training data.

## Architecture

Retrieval is **not** implemented inside `api_v2` — it's a separate
service, `Backend/ragulate-rag/` (FastAPI + LightRAG + Neo4j), copied
from GRIPL-v2's `gripl-rag` pipeline. It has its own Neo4j knowledge
graph and its own document corpus, entirely separate from GRIPL's
instance — different projects want different knowledge, and this
pipeline can't partition one graph per consumer, so each project runs
its own copy rather than sharing one running instance. See
`Backend/ragulate-rag/` for the ingestion scripts and its own `.env`.

## Pipeline

1. User sends a chat message
2. `rag_service.py` sends **only that message** (not the conversation
   history) to `ragulate-rag`'s `POST /api/query` — LightRAG has no
   multi-turn concept, which is exactly why an earlier attempt at RAG in
   this codebase stalled (see `Common/General` meeting notes,
   2026-03-24)
3. `ragulate-rag` returns retrieved, source-attributed chunks (plus
   graph entities/relationships) from its Neo4j-backed knowledge graph
4. `rag_service.py` formats those chunks into a system message, injected
   between the system prompt and the (full) conversation history
5. The LLM call proceeds exactly as before, now with that extra context
6. If `ragulate-rag` is unset or unreachable, this degrades gracefully
   to plain LLM chat rather than failing the request

## Implementation

`Backend/api_v2/app/services/rag_service.py` — calls out to
`ragulate-rag` and builds the final message list; the actual LLM call
stays in `llm_service.py`, unchanged.

`Backend/ragulate-rag/app/` — the retrieval service itself: LightRAG
wrapper (`rag/engine.py`), ingestion (`rag/ingestion.py`,
`scripts/ingest.py`, offline/batch only — no ingestion API), and the
query/PDF-source/evaluation routes (`api/`).

## Supported LLM Providers (chat)

- OpenRouter API

(Ollama was previously listed here but isn't wired into `llm_service.py`
today — leaving it out until it actually is, rather than documenting an
aspiration as if it were implemented.)
