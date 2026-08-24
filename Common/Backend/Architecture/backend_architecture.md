# Backend Architecture

This document describes the architecture and internal structure of the
backend. It explains how requests flow through the system and where
specific functionality is implemented.

The backend is built using **FastAPI**, **MongoDB**, and a modular
**service-based architecture**. The system integrates **Large Language
Models (LLMs)** and a **RAG (Retrieval Augmented
Generation)** pipeline.

**Authentication is not part of this backend.** User accounts, password
hashing, and JWT issuance live in a separate, standalone service —
[`auth-service`](https://github.com/DBIS-Legal-LLMs/auth-service), shared
with GRIPL and future DBIS tools. This backend only verifies tokens
against that service's published JWKS (`core/jwt_verification.py`); it
never stores credentials and no longer has a `users` collection.

---

# System Overview

The backend is structured into several logical layers:

Frontend / Client → API Layer (FastAPI Routes) → Dependencies (Auth /
DB) → Service Layer (Business Logic) → Chat System (LLM / RAG) →
Database (MongoDB)

Each layer has a clearly defined responsibility.

Layer Responsibility

---

API Layer HTTP endpoints and request validation
Dependencies Authentication and database injection
Service Layer Business logic
Chat System Interaction with LLMs and RAG
Core Utilities Security, config, error codes
Models Data schemas
Database Persistent data storage

---

# Request Flow

### 1. Request from the Frontend

Example:

POST /api/chat/{chat_id}/messages

The request contains the user message that should be processed.

### 2. API Layer

Handled by FastAPI routers located in:

api/routes/

Routes are responsible for:

- receiving HTTP requests
- validating input
- calling services
- returning responses

Routes should not contain business logic.

### 3. Dependencies

Defined in:

core/deps.py

Responsibilities:

- verify the JWT against auth-service's JWKS (core/jwt_verification.py) —
  no local user lookup, the verified token's subject *is* the user id
- inject database connection

### 4. Service Layer

Located in:

services/

Main services:

- ChatService
- FolderService
- RAGService

(`UserService` used to live here — it moved to `auth-service` along with
the rest of authentication.)

Responsibilities include:

- creating chats
- storing messages
- managing folder structure
- preparing LLM prompts
- interacting with the database

### 5. Building LLM Context

When generating an LLM response:

1.  User message is stored
2.  Chat history is retrieved
3.  History is formatted into an LLM prompt

### 6. LLM / RAG Processing

Supported provider: **OpenRouter** (the only one actually wired into
`llm_service.py` today, despite other providers being mentioned
elsewhere as future/config-level options).

Before calling the LLM, `rag_service.py` queries `ragulate-rag` — a
separate FastAPI + LightRAG + Neo4j service (`Backend/ragulate-rag/`,
copied from GRIPL's `gripl-rag` pipeline, own instance/corpus, see
`Common/Backend/Architecture/rag_system.md`) — with just the latest
message, and injects the retrieved, source-attributed context into the
prompt. Falls back to plain LLM chat if that service is unset or
unreachable.

Implementation:

services/rag_service.py (retrieval + prompt assembly), services/llm_service.py (the LLM call itself)

### 7. Storing the Response

The generated response is:

- stored as an assistant message
- added to the conversation history
- returned to the frontend

---

# Summary

The backend separates responsibilities across different layers to
ensure:

- modularity
- maintainability
- scalability
