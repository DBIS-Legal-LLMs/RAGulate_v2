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

## Features

1. **User Authentication**
   - JWT-based login and registration.
   - Role-based access control.

2. **Session & Folder Management**
   - Organise chats in a single folder layer; chats can belong to a folder or remain as top-level chats.
   - Create, rename, and delete folders and chat sessions.

3. **Streaming Chat**
   - Messages are streamed token-by-token from the LLM for a responsive UX.
   - Full conversation history is passed to the LLM to maintain context.

4. **LLM Provider**
   - Uses **OpenRouter** (cloud) for LLM inference.
   - Provider and model are configurable via environment variables and user settings.

5. **RAG Pipeline** *(in progress)*
   - The `rag_service` layer is prepared for document retrieval augmentation.
   - Currently acts as a plain LLM chat service; retrieval injection will be added without touching higher-level services.

6. **Persistent Storage (MongoDB)**
   - Collections: `users`, `folders`, `chat_sessions`, `chat_messages`.
   - Indexes are created automatically on startup for fast sorting and lookups.

## Project Structure

```
RAGulate_v2/
├── Backend/
│   ├── api_v2/app/          # FastAPI application
│   │   ├── api/routes/      # HTTP endpoints (auth, chat, folders, users, models)
│   │   ├── core/            # Auth/JWT utilities, dependencies
│   │   ├── db/              # MongoDB connection
│   │   ├── models/          # Pydantic schemas
│   │   └── services/        # Business logic (chat, folder, user, RAG, LLM)
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
- [Node.js](https://nodejs.org/) ≥ 18 and [pnpm](https://pnpm.io/)
- An [OpenRouter API key](https://openrouter.ai/)

> **Detailed step-by-step guides** (Anaconda, Docker, Docker GPU support, MongoDB shell usage, deploying as a systemd service, and patching the backend) are available under [`Common/Backend/Setup/`](Common/Backend/Setup/).

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
| `JWT_SECRET` | A long random string used to sign tokens |
| `JWT_ALGORITHM` | `HS256` (default) |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime in minutes (e.g. `60`) |
| `OPENROUTER_API_KEY` | Your OpenRouter API key |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` |
| `OPENROUTER_MODEL` | E.g. `mistralai/mistral-nemo` |
| `OPENROUTER_EMBEDDINGS_MODEL` | Embeddings model on OpenRouter |

### 3. Start the Backend (Docker)
```bash
cd Backend
docker compose up --build
```

This starts:
- **`ragulate_mongodb`** – MongoDB on port `27017`
- **`ragulate_backend_v2`** – FastAPI on port `8000`

The API docs are available at `http://localhost:8000/docs` once running.

> **GPU support**: see [`Common/Backend/Setup/5_Docker_GPU_Support.md`](Common/Backend/Setup/5_Docker_GPU_Support.md).

### 4. Start the Frontend
```bash
cd Frontend
pnpm install
pnpm dev
```

The frontend is available at `http://localhost:3000`.

---

## Useful Docker Commands

```bash
# Show running containers
docker ps

# Follow backend logs
docker logs -f ragulate_backend_v2

# Open a shell inside the backend container
docker exec -it ragulate_backend_v2 bash

# Open a shell inside MongoDB
docker exec -it ragulate_mongodb bash
```

See [`Common/Backend/Setup/6_Docker_Service.md`](Common/Backend/Setup/6_Docker_Service.md) and [`Common/Backend/Setup/7_MongoDB_Tutorial.md`](Common/Backend/Setup/7_MongoDB_Tutorial.md) for more.

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
- Complete the RAG retrieval pipeline in `rag_service.py`
- Add reranking for better retrieval quality
- Implement graceful backend shutdown
- Allow custom session names
- Improve markdown rendering in the chat UI (lists, code blocks)
