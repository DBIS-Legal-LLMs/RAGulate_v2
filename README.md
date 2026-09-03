# RAGulate_v2 - LegalQA Chatbot

## Overview
RAGulate is a Masters project implementing a Legal Question-Answering chatbot using Retrieval-Augmented Generation (RAG) technology. The system provides a session-based chat interface backed by a modular FastAPI service that integrates with external LLM providers (OpenRouter) and stores all data in MongoDB.

## Tech Stack

<p align="left">
<img src="https://skillicons.dev/icons?i=next,react,tailwind,ts,mongodb,fastapi,docker"/>
</p>

- [Next.js 15](https://nextjs.org/) (App Router)
- [React 19](https://react.dev/)
- [Tailwind CSS](https://tailwindcss.com/) (UI Styling)
- [MongoDB](https://www.mongodb.com/) (Database)
- [FastAPI](https://fastapi.tiangolo.com/) (Backend API)
- [Docker](https://www.docker.com/) / [Docker Compose](https://docs.docker.com/compose/) (Deployment)

## Authentication

User accounts, login/registration, and JWT issuance are **not** handled by this repository anymore — they live in [`auth-service`](https://github.com/DBIS-Legal-LLMs/auth-service), a standalone identity service shared with GRIPL and future DBIS tools. This backend only *verifies* tokens: it fetches `auth-service`'s public signing key from its JWKS endpoint (`core/jwt_verification.py`) and trusts any request bearing a validly-signed, unexpired token — it never sees a password and no longer stores a `users` collection of its own.

Practically, this means:
- `auth-service` must be running and reachable (see its own README) before login/register work anywhere against this backend.
- The `AUTH_SERVICE_URL` env var (below) points this backend at it.
- Endpoints that used to live here (`/api/auth/*`, username changes) have moved to `auth-service` and its future `/users/me` — nothing to configure on this side beyond the URL.

## Features

1. **User Authentication**
   - Delegated to `auth-service` (see [Authentication](#authentication) above) — this backend only verifies.
   - Role-based access control *(planned — `auth-service` carries a per-app role claim once implemented; not yet enforced anywhere)*.

2. **Session & Folder Management**
   - Organise chats in a single folder layer; chats can belong to a folder or remain as top-level chats.
   - Create, rename, and delete folders and chat sessions.

3. **Streaming Chat**
   - Messages are streamed token-by-token from the LLM for a responsive UX.
   - Full conversation history is passed to the LLM to maintain context.

4. **LLM Provider**
   - Uses **OpenRouter** (cloud) for LLM inference.
   - Provider and model are configurable via environment variables and user settings.

5. **RAG Pipeline**
   - `rag_service.py` retrieves context from **`ragulate-rag`** (`Backend/ragulate-rag/`) — RAGulate's own FastAPI + LightRAG + Neo4j service, copied from GRIPL's `gripl-rag` pipeline and seeded with the same GDPR regulation + EDPB guidance documents as a starting corpus (own instance, own graph — not shared with GRIPL, since different projects want different knowledge; see that folder's own notes for why).
   - Retrieval is single-turn (only the latest message is used as the query — LightRAG has no multi-turn concept) while the full conversation history still goes to the answer-generating LLM call as before.
   - Optional: if `ragulate-rag` is unset or unreachable, chat still works as plain LLM output, just without retrieval.

6. **Persistent Storage (MongoDB)**
   - Collections: `folders`, `chat_sessions`, `chat_messages` — all reference a `user_id` issued by `auth-service`, not a local `users` collection (that moved out along with authentication, see [Authentication](#authentication)).
   - Indexes are created automatically on startup for fast sorting and lookups.

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

## Installation Guide

### Prerequisites
- [Docker](https://docs.docker.com/engine/install/) & [Docker Compose](https://docs.docker.com/compose/install/)
- [Node.js](https://nodejs.org/) **≥ 20.10** — `Frontend/next.config.mjs` uses import-attributes syntax (`import ... with { type: 'json' }`) that older Node can't parse. Use [nvm](https://github.com/nvm-sh/nvm) if your system Node is older than that. [pnpm](https://pnpm.io/) is what's committed (`pnpm-lock.yaml`), but plain `npm install --legacy-peer-deps` / `npm run dev` work fine too if you don't have pnpm installed — see step 4 below.
- An [OpenRouter API key](https://openrouter.ai/)
- A running instance of [`auth-service`](https://github.com/DBIS-Legal-LLMs/auth-service) — login/register won't work without it. See that repo's README to set it up; by default this backend expects it at `http://localhost:8100`.

> **Detailed step-by-step guides** (Anaconda, Docker, Docker GPU support, MongoDB shell usage, deploying as a systemd service, patching the backend, and a [full local dev/testing walkthrough](Common/Backend/Setup/9_Full_Local_Testing_Walkthrough.md) covering per-service logs, inspecting MongoDB/Neo4j directly, and resetting the RAG corpus) are available under [`Common/Backend/Setup/`](Common/Backend/Setup/).

---

### 1. Clone the repository
```bash
git clone <repo-url>
cd RAGulate_v2
```

### 2. Configure environment variables
Copy the example file and fill in the values:
```bash
cp .env.example Backend/.env
```

Open `Backend/.env` and set:

| Variable | Description |
|---|---|
| `APP_ENV` | `local` (local machine) or `docker` (container) |
| `MONGO_URL` | MongoDB connection string (default: `mongodb://mongodb:27017`) |
| `MONGO_DB_NAME` | Name of the database |
| `AUTH_SERVICE_URL` | Base URL of `auth-service` — this backend fetches its JWKS from `{AUTH_SERVICE_URL}/.well-known/jwks.json` to verify tokens. Running locally: `http://localhost:8100`. Running this backend via Docker while `auth-service` also runs in Docker on the same host: `http://host.docker.internal:8100`. |
| `CORS_ALLOWED_ORIGINS` | Comma-separated browser origins allowed to call this API. Default (`http://localhost:3000`) matches the frontend's default port — only change this if your frontend runs on a different port/host, otherwise login fails with a CORS error in the browser console. |
| `OPENROUTER_API_KEY` | Your OpenRouter API key |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` |
| `OPENROUTER_MODEL` | E.g. `mistralai/mistral-nemo` |
| `OPENROUTER_EMBEDDINGS_MODEL` | Embeddings model on OpenRouter |
| `RAGULATE_RAG_URL` | Base URL of `ragulate-rag` (below). Optional — chat still works without it, just without retrieval |
| `RAGULATE_RAG_TIMEOUT` | Seconds to wait for a `ragulate-rag` response before falling back to plain chat (default 60) |

Also copy `ragulate-rag/.env.example` to `ragulate-rag/.env` and fill in an LLM/embedding API key (used for the RAG service's own entity extraction, separate from the chat LLM call above).

### 3. Start the Backend (Docker)
```bash
cd Backend
docker compose up --build
```

This starts:
- **`ragulate_mongodb`** – MongoDB on port `27017`
- **`ragulate_backend_v2`** – FastAPI on port `8000`
- **`ragulate_rag`** – RAGulate's own RAG service on port `8181` (see `Backend/ragulate-rag/`)
- **`ragulate_neo4j`** – knowledge graph backing `ragulate_rag`, browser UI on port `7475`

The API docs are available at `http://localhost:8000/docs` once running.

> **Chat works fine without this step** — RAG retrieval is optional; without it, chat just falls back to plain LLM output with no GDPR context injected. Skip this entirely for basic testing (login, folders, chat UI) and only come back to it once you actually need retrieval to work.

The GDPR corpus (PDFs + extracted text) ships already checked in, but the knowledge graph itself has to be built once by running the ingestion script. **This is slow and costs real API usage** — a full run of all 37 documents took ~6 hours in testing (entity/relationship extraction makes an LLM call per chunk). Do this once, with your own key, not repeatedly — see [Ingestion storage](Common/Backend/Architecture/rag_system.md#ingestion-storage) for why the ingested data survives container restarts and rebuilds, so a one-time run is all you should ever need for local testing.

Run it **inside the running container**, not on the host — `ragulate-rag`'s LightRAG storage (`RAG_WORKING_DIR`) lives in a Docker volume mounted into the container; a host-side `python scripts/ingest.py` writes to a plain folder on your machine instead and the query service will never see that data:
```bash
docker compose exec ragulate-rag python scripts/ingest.py
```
(Running `ragulate-rag` directly, not via Docker Compose? Then `cd Backend/ragulate-rag && python scripts/ingest.py` on the host is correct — it's the same process reading `./rag_working_dir` either way.)

> **GPU support**: see [`Common/Backend/Setup/5_Docker_GPU_Support.md`](Common/Backend/Setup/5_Docker_GPU_Support.md).

### 4. Start the Frontend
```bash
cd Frontend
cp .env.example .env.local
pnpm install
pnpm dev
```
No `pnpm`? `npm install --legacy-peer-deps && npm run dev` works too (the `--legacy-peer-deps` flag works around a pre-existing `date-fns`/`react-day-picker` version conflict; without it, plain `npm install` fails). You'll see harmless `pnpm: not found` warnings from a lockfile-patch step Next.js runs — the dev server still starts fine.

The frontend is available at `http://localhost:3000`. Login and registration are called directly against `auth-service` from the browser (`NEXT_PUBLIC_AUTH_SERVICE_URL` in `Frontend/.env.example`, default `http://localhost:8100`) — the session (token + username) persists in `localStorage` across a page reload, and Log out lives in the profile dropdown beneath Settings.

---

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

---

## Deploying updates (patch workflow)
```bash
sudo systemctl stop ragulate.service
git pull
sudo systemctl start ragulate.service
docker logs -f ragulate_backend_v2
```

Full instructions: [`Common/Backend/Setup/8_Backend_Patchen.md`](Common/Backend/Setup/8_Backend_Patchen.md).

---

## TODOs
- Add reranking for better retrieval quality (`ragulate-rag` supports it, off by default)
- Show sources/citations for retrieved context in the chat UI (`ragulate-rag`'s responses already carry per-chunk source attribution — this is a frontend task)
- Implement graceful backend shutdown
- Allow custom session names
- Improve markdown rendering in the chat UI (lists, code blocks)
- Extract `ragulate-rag`'s pipeline into a standalone template repo, generalized beyond GDPR, once another project wants its own instance
