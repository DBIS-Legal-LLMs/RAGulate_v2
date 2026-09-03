# 9. Full Local Testing Walkthrough

A start-to-finish guide for running the whole system locally for testing:
`auth-service` → RAGulate's backend stack (Mongo, `api_v2`, `ragulate-rag`,
Neo4j) → the frontend — plus how to look inside each piece while it's
running (logs, MongoDB, Neo4j) and how to reset/re-ingest the RAG corpus.

This assumes you've already done the one-time setup in the main
[README](../../../README.md) (env files copied and filled in, an OpenRouter
key, `auth-service` cloned locally). This doc is the *repeatable* loop you
run every time you sit down to test, not the first-time setup.

## 0. The three stacks, and why the order matters

| # | Stack | Repo/dir | Must be up before |
|---|---|---|---|
| 1 | `auth-service` | `auth-service/` (sibling repo) | RAGulate backend and frontend — both need it for login/JWKS verification |
| 2 | RAGulate backend | `RAGulate_v2/Backend/` | the frontend |
| 3 | RAGulate frontend | `RAGulate_v2/Frontend/` | last |

Nothing hard-crashes if you start them out of order — the backend logs a
JWKS-fetch error until `auth-service` is reachable, and the frontend just
shows failed requests — but starting in this order avoids chasing errors
that are really just "the thing it depends on isn't up yet."

## 1. Start `auth-service`

```bash
cd /home/buzzy/Projects/master/magda/auth-service
docker compose up -d
```

Containers: `auth-service` (FastAPI, `http://localhost:8100`) and
`auth-mongo` (MongoDB, **not** exposed to the host — internal only).

Check it's actually up:
```bash
curl -s http://localhost:8100/.well-known/jwks.json
```
A JSON key set back means it's healthy.

## 2. Start the RAGulate backend stack

```bash
cd /home/buzzy/Projects/master/magda/RAGulate_v2/Backend
docker compose up -d --build
```

Containers started: `ragulate_mongodb`, `ragulate_backend_v2`,
`ragulate_rag`, `ragulate_neo4j`. `ragulate-rag` warms up its LightRAG
engine (local reranker model, Neo4j indices) on its own startup — wait for
that to finish before testing chat, or the first query while it's still
warming up will just queue behind it:

```bash
docker compose logs -f ragulate-rag
# wait for: "LightRAG engine warm and ready."
# Ctrl+C once you see it — the service is already up either way
```

Confirm the backend itself is up:
```bash
curl -s http://localhost:8000/api/health
```

## 3. (Re-)ingest the RAG corpus

Skip this step entirely if you've already ingested and haven't wiped the
volume or changed any source documents since — **ingested data survives
container restarts and rebuilds** (it lives in the named Docker volumes
`ragulate_rag_working_dir` and `ragulate_neo4j_data`, not in the container
itself). You only need to (re-)run this after a fresh volume or after
editing/adding source documents.

```bash
docker compose exec ragulate-rag python scripts/ingest.py
```

Run this **inside the container**, not on the host — see
[`Architecture/rag_system.md`](../Architecture/rag_system.md#ingestion-storage)
for why a host-side run silently writes to the wrong place. This makes
real LLM calls for entity extraction across the whole corpus — a full run
of all 37 documents took **~6 hours** in testing. Kick it off, let it run
in the background, and don't repeat it unnecessarily; it's a one-time
cost per volume (see above). You'll see:
```
============================================================
INGESTION COMPLETE
============================================================
  Documents:  37/37 successful
  Time:       <a real, non-trivial duration>
```
If it instead says `WARNING: No new unique documents were found` and
finishes in a fraction of a second for every file, nothing was actually
ingested — see the note on dedup below.

### Resetting the corpus (wipe + re-ingest from scratch)

LightRAG dedupes by filename, not content — if you edit a source
document's text but keep the same filename, a plain re-run of
`ingest.py` will skip it as an existing duplicate and silently keep the
old content. There's no per-document delete/update wired up in this
codebase yet, so the only way to force a real re-ingest today is a full
wipe:

```bash
cd /home/buzzy/Projects/master/magda/RAGulate_v2/Backend
docker compose down ragulate-rag ragulate-neo4j
docker volume rm backend_ragulate_rag_working_dir backend_ragulate_neo4j_data
docker compose up -d --build ragulate-rag ragulate-neo4j
docker compose logs -f ragulate-rag   # wait for "warm and ready" again
docker compose exec ragulate-rag python scripts/ingest.py
```

(Volume names are prefixed with the Compose project name — `backend_` by
default, since `Backend/` is the directory `docker-compose.yml` lives in.
Run `docker volume ls | grep ragulate` first if you're not sure of the
exact names on your machine.)

### Sanity-check retrieval directly (skips the frontend/LLM entirely)

```bash
curl -s -X POST http://localhost:8181/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is a data protection impact assessment?", "mode": "hybrid"}'
```
Look for non-empty `documents`/entities in the response. An empty result
here means the problem is in `ragulate-rag`/the corpus, not in the chat
backend or frontend — worth checking before assuming a chat-side bug.

## 4. Start the frontend

```bash
cd /home/buzzy/Projects/master/magda/RAGulate_v2/Frontend
npm install --legacy-peer-deps   # first time only, or after a pull that touched package.json
npm run dev
```

- **Node version**: needs **Node 20.10+** (`next.config.mjs` uses
  `import ... with { type: 'json' }`, an import-attributes syntax older
  Node doesn't parse). If your system Node is older, install a newer one
  via [nvm](https://github.com/nvm-sh/nvm) rather than replacing your
  system Node — `nvm install 22 && nvm use 22`.
- **npm vs pnpm**: the repo has a committed `pnpm-lock.yaml`, but plain
  `npm install`/`npm run dev` work fine too — you'll see harmless
  `pnpm: not found` warnings during a lockfile-patch step Next.js runs;
  the dev server still starts normally. `--legacy-peer-deps` works around
  a pre-existing version conflict between `date-fns` and
  `react-day-picker` — without it `npm install` fails outright.
- Open `http://localhost:3000`, register/log in (goes straight to
  `auth-service`, not through this backend), and start a chat.

## 5. Watching logs

Each service's logs, followed live:

```bash
# RAGulate backend stack (run from RAGulate_v2/Backend/)
docker compose logs -f ragulate_backend_v2   # chat/folder API, LLM calls, RAG fallback traces
docker compose logs -f ragulate-rag          # retrieval queries, ingestion progress, LightRAG internals
docker compose logs -f ragulate_neo4j        # graph DB
docker compose logs -f ragulate_mongodb      # rarely useful — Mongo's own startup/checkpoint noise

# auth-service (run from auth-service/)
docker compose logs -f auth-service          # register/login requests, JWT issuance
```

Or by container name from anywhere, without `cd`-ing into either
project's directory:
```bash
docker logs -f ragulate_backend_v2
docker logs -f ragulate_rag
docker logs -f auth-service
```

Frontend logs are just whatever `npm run dev` prints to the terminal
you ran it in — no separate log command.

## 6. Inspecting the databases directly

### MongoDB — RAGulate's own data (folders, chat sessions, chat messages)

```bash
docker exec -it ragulate_mongodb mongosh
```
Then, inside the `mongosh` shell:
```js
use <your MONGO_DB_NAME from Backend/.env>
show collections                          // folders, chat_sessions, chat_messages
db.chat_sessions.find().sort({updated_at: -1}).limit(5).pretty()
db.folders.find().pretty()
db.chat_messages.find({session_id: "<id from above>"}).sort({created_at: 1}).pretty()
```

### MongoDB — auth-service's users

`auth-mongo` isn't exposed to the host on purpose (see its
`docker-compose.yml` — no `ports:` mapping), so you have to shell in via
Docker rather than connecting from a host-installed `mongosh`:
```bash
docker exec -it auth-mongo mongosh
```
```js
use <your MONGO_DB_NAME from auth-service/.env>
db.users.find({}, {hashed_password: 0}).pretty()   // exclude the hash, just to be tidy
```

### Neo4j — the RAG knowledge graph

Browser UI: **http://localhost:7475** — login `neo4j` /
`ragulate-rag-2026` (from `Backend/docker-compose.yml`'s `NEO4J_AUTH`).
Useful first query to confirm ingestion actually wrote something:
```cypher
MATCH (n) RETURN n LIMIT 25
```
Or via `cypher-shell` without leaving the terminal:
```bash
docker exec -it ragulate_neo4j cypher-shell -u neo4j -p ragulate-rag-2026 \
  "MATCH (n) RETURN count(n) AS node_count"
```
A `node_count` of 0 after ingestion "succeeded" is the same red flag as
an empty `/api/query` response above — the corpus never actually landed.

## 7. Shutting everything down

```bash
cd /home/buzzy/Projects/master/magda/RAGulate_v2/Backend && docker compose down
cd /home/buzzy/Projects/master/magda/auth-service && docker compose down
```
Leaving off `-v` (the default here) keeps every named volume intact —
Mongo data, the RSA signing key, the RAG corpus — so the next `docker
compose up` picks up right where you left off. Only add `-v` if you
specifically want to wipe one of those (see the reset instructions in
step 3 for the RAG-specific case).
