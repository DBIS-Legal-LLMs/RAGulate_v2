# RAGulate_v2 - LegalQA Chatbot

A Masters project implementing a Legal Question-Answering chatbot using
Retrieval-Augmented Generation (RAG): a session-based chat UI backed by a
FastAPI service, OpenRouter for LLM inference, and MongoDB for storage.

<p align="left">
<img src="https://skillicons.dev/icons?i=next,react,tailwind,ts,mongodb,fastapi,docker"/>
</p>

**[Features](#features) · [Project Structure](#project-structure) · [Authentication](#authentication) · [Installation Guide](#installation-guide) · [Quick Start (Already Installed)](#quick-start-already-installed) · [Useful Docker Commands](#useful-docker-commands) · [TODOs](#todos)**

---

## Features

- **Authentication** — delegated to `auth-service` (see [below](#authentication)); this backend only verifies tokens. Role-based access control is *planned*, not yet enforced.
- **Session & folder management** — create, rename, and delete chats and folders; a chat can live in a folder or stand alone.
- **Streaming chat** — token-by-token responses; full conversation history goes to the LLM for context.
- **LLM provider** — OpenRouter (cloud), model/provider configurable via env vars and user settings.
- **RAG pipeline** — `ragulate-rag` (`Backend/ragulate-rag/`, own FastAPI + LightRAG + Neo4j instance, seeded with GDPR regulation + EDPB guidance) supplies retrieved context. Retrieval is single-turn (latest message only); optional — chat still works as plain LLM output if it's unset or unreachable.
- **Persistent storage** — MongoDB collections `folders`, `chat_sessions`, `chat_messages`, all keyed by the `user_id` `auth-service` issues (no local `users` collection anymore).

## Project Structure

```
RAGulate_v2/
├── Backend/
│   ├── api_v2/app/          # FastAPI application
│   │   ├── api/routes/      # HTTP endpoints (chat, folders, models)
│   │   ├── core/            # JWT verification against auth-service's JWKS, dependencies
│   │   ├── db/              # MongoDB connection
│   │   ├── models/          # Pydantic schemas
│   │   └── services/        # Business logic (chat, folder, user, RAG, LLM)
│   ├── ragulate-rag/        # RAGulate's own RAG service (FastAPI + LightRAG + Neo4j)
│   │   ├── data/             # GDPR PDFs + extracted text (starting corpus)
│   │   ├── scripts/          # extract_pdfs.py, ingest.py (offline, no ingestion API)
│   │   └── .env              # (created from ragulate-rag/.env.example)
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── requirements.txt
│   └── .env                 # (created from .env.example)
├── Frontend/                # Next.js application
├── Common/
│   ├── Backend/
│   │   ├── Setup/           # Step-by-step setup guides
│   │   └── Architecture/    # Architecture & schema docs
│   └── General/             # Meeting notes
└── .env.example
```

## Authentication

User accounts, login/registration, and JWT issuance live in
[`auth-service`](https://github.com/DBIS-Legal-LLMs/auth-service), a standalone
identity service shared with GRIPL and future DBIS tools. This backend only
*verifies* tokens — it fetches `auth-service`'s public signing key from its
JWKS endpoint (`core/jwt_verification.py`) and trusts any request bearing a
validly-signed, unexpired token. It never sees a password and holds no
`users` collection of its own.

- `auth-service` must be running and reachable before login/register work
  anywhere against this backend (see its own README).
- `AUTH_SERVICE_URL` (below) points this backend at it.
- The frontend talks to `auth-service` directly for login/register
  (`NEXT_PUBLIC_AUTH_SERVICE_URL`) — not through this backend.

## Installation Guide

### Prerequisites
- [Docker](https://docs.docker.com/engine/install/) & [Docker Compose](https://docs.docker.com/compose/install/)
- [Node.js](https://nodejs.org/) **≥ 20.10** — `Frontend/next.config.mjs` uses import-attributes syntax older Node can't parse. Use [nvm](https://github.com/nvm-sh/nvm) if needed. [pnpm](https://pnpm.io/) is what's committed (`pnpm-lock.yaml`); plain `npm install --legacy-peer-deps` also works.
- An [OpenRouter API key](https://openrouter.ai/)
- A running instance of [`auth-service`](https://github.com/DBIS-Legal-LLMs/auth-service) — see that repo's README. Default expected address: `http://localhost:8100`.

> **Detailed step-by-step guides** (Anaconda, Docker, Docker GPU support, MongoDB shell usage, and a [full local dev/testing walkthrough](Common/Backend/Setup/9_Full_Local_Testing_Walkthrough.md) covering per-service logs, inspecting MongoDB/Neo4j directly, and resetting the RAG corpus) live under [`Common/Backend/Setup/`](Common/Backend/Setup/).

### 1. Clone and configure

```bash
git clone <repo-url>
cd RAGulate_v2
cp .env.example Backend/.env
cp Backend/ragulate-rag/.env.example Backend/ragulate-rag/.env   # fill in an LLM/embedding key for the RAG service's own entity extraction
```

Open `Backend/.env` and set:

| Variable | Description |
|---|---|
| `APP_ENV` | `local` (host machine) or `docker` (container) |
| `MONGO_URL` | MongoDB connection string (default: `mongodb://mongodb:27017`) |
| `MONGO_DB_NAME` | Name of the database |
| `AUTH_SERVICE_URL` | Base URL of `auth-service` — JWKS fetched from `{AUTH_SERVICE_URL}/.well-known/jwks.json`. Running locally: `http://localhost:8100`. This backend in Docker, `auth-service` also in Docker on the same host: `http://host.docker.internal:8100`. |
| `CORS_ALLOWED_ORIGINS` | Browser origins allowed to call this API. Default (`http://localhost:3000`) matches the frontend's default port — wrong value shows up as a CORS error on login, not a backend error. |
| `OPENROUTER_API_KEY` / `OPENROUTER_BASE_URL` / `OPENROUTER_MODEL` / `OPENROUTER_EMBEDDINGS_MODEL` | OpenRouter credentials + model choice |
| `RAGULATE_RAG_URL` | Base URL of `ragulate-rag`. Optional — chat works without it, just without retrieval |
| `RAGULATE_RAG_TIMEOUT` | Seconds to wait for a `ragulate-rag` response before falling back to plain chat (default `180` — real hybrid-mode queries against a populated corpus legitimately take 60–120s+) |

And in `Frontend/.env.local` (copy from `Frontend/.env.example`):

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_AUTH_SERVICE_URL` | Where the browser calls `auth-service` directly for login/register/logout (default `http://localhost:8100`) |
| `NEXT_PUBLIC_API_BACKEND` | This backend's own URL (default `http://localhost:8000`) |

### 2. Start the Backend

```bash
cd Backend
docker compose up --build
```

Starts `ragulate_mongodb` (`:27017`), `ragulate_backend_v2` (`:8000`,
docs at `/docs`), `ragulate_rag` (`:8181`), and `ragulate_neo4j` (`:7475`).

> **Chat works without RAG** — it's optional; skip straight to testing login/folders/chat and come back once you actually need retrieval.

The GDPR corpus ships as PDFs already checked in, but the knowledge graph has
to be built once via ingestion — **slow and costs real API usage** (~6h for
all 37 documents; an LLM call per chunk). Run it once, **inside the running
container** (its storage lives in a Docker volume the host process can't see):

```bash
docker compose exec ragulate-rag python scripts/ingest.py
```

> **GPU support**: [`Common/Backend/Setup/5_Docker_GPU_Support.md`](Common/Backend/Setup/5_Docker_GPU_Support.md).

### 3. Start the Frontend

```bash
cd Frontend
cp .env.example .env.local
pnpm install
pnpm dev
```

No `pnpm`? `npm install --legacy-peer-deps && npm run dev` works too (the
flag works around a `date-fns`/`react-day-picker` version conflict).

→ **http://localhost:3000**. Login/registration go straight to `auth-service`
from the browser; the session persists in `localStorage` across reloads; Log
out lives in the profile dropdown beneath Settings.

## Quick Start (Already Installed)

Everything above already done once (`.env` files filled in, `pnpm install`
run, images built) — just bringing it back up:

```bash
# auth-service must be running first — see its own README
cd Backend && docker compose up -d          # mongodb + backend (+ rag + neo4j)
# only need chat, not retrieval? skip the RAG stack:
docker compose up -d mongodb backend

cd Frontend && pnpm dev                     # or: npm run dev
```

Health check: `curl http://localhost:8000/api/health` →
`{"status":"ok","service":"gdpr-backend-v2"}`. Backend docs: `http://localhost:8000/docs`. Frontend: `http://localhost:3000`.

## Useful Docker Commands

```bash
# Show running containers
docker ps

# Follow logs for each backend piece
docker logs -f ragulate_backend_v2   # chat/folder API, LLM calls, RAG fallback traces
docker logs -f ragulate_rag          # retrieval queries, ingestion progress
docker logs -f ragulate_neo4j        # graph DB
docker logs -f auth-service          # register/login, JWT issuance (separate compose project)

# Open a shell inside a container
docker exec -it ragulate_backend_v2 bash

# Open a MongoDB shell
docker exec -it ragulate_mongodb mongosh
```

See [`Common/Backend/Setup/6_Docker_Service.md`](Common/Backend/Setup/6_Docker_Service.md), [`Common/Backend/Setup/7_MongoDB_Tutorial.md`](Common/Backend/Setup/7_MongoDB_Tutorial.md), and — for the full loop including Neo4j inspection and resetting the RAG corpus — [`Common/Backend/Setup/9_Full_Local_Testing_Walkthrough.md`](Common/Backend/Setup/9_Full_Local_Testing_Walkthrough.md).

## TODOs
- Add reranking for better retrieval quality (`ragulate-rag` supports it, off by default)
- Show sources/citations for retrieved context in the chat UI (`ragulate-rag`'s responses already carry per-chunk source attribution — this is a frontend task)
- Implement graceful backend shutdown
- Allow custom session names
- Improve markdown rendering in the chat UI (lists, code blocks)
- Extract `ragulate-rag`'s pipeline into a standalone template repo, generalized beyond GDPR, once another project wants its own instance
