# Enterprise AI Document Intelligence Platform

A production-grade, multi-agent RAG (Retrieval-Augmented Generation) system for uploading documents and asking questions about them — with citations, streaming responses, and intelligent query routing across specialized AI agents.

Built end-to-end: FastAPI backend, PostgreSQL + pgvector for semantic search, LangGraph for multi-agent orchestration, React frontend with real-time streaming chat, full JWT authentication, and Dockerized for one-command local deployment.

## Live Demo

- **App:** [link once deployed]
- **API docs:** [Railway backend URL]/docs

## Features

- **JWT authentication** — register/login/refresh with short-lived access tokens and rotating refresh tokens
- **Document ingestion** — upload PDF, DOCX, or TXT files; automatic text extraction and recursive, token-aware chunking (via `tiktoken`)
- **Semantic search** — Cohere embeddings (`embed-english-v3.0`) stored in PostgreSQL via `pgvector`, with an HNSW index for fast cosine-similarity search
- **Multi-agent RAG** — a LangGraph pipeline routes each query to a specialized agent:
  - **QA agent** — answers specific questions using retrieved context
  - **Summarizer agent** — produces a coherent overview of a document (uses full-document retrieval in order, not similarity search — see *Design Decisions* below)
  - **Analysis agent** — identifies themes, entities, and stakeholders
- **Citations** — every answer links back to the exact source chunks it was generated from (full text, filename, chunk index, similarity score)
- **Streaming responses** — answers stream token-by-token via Server-Sent Events (SSE)
- **Interaction logging** — every chat request is logged (query, route taken, answer, latency) for observability
- **Rate limiting** — per-endpoint limits (via `slowapi`) protect against abuse and control API costs
- **Fully Dockerized** — one `docker compose up` runs Postgres, backend, and frontend together

## Architecture
┌─────────────┐ ┌──────────────┐ ┌─────────────────┐
│ React │─────▶│ FastAPI │─────▶│ PostgreSQL │
│ (nginx) │◀─────│ backend │◀─────│ + pgvector │
└─────────────┘ SSE └──────┬───────┘ └─────────────────┘
│
▼
┌───────────────┐
│ LangGraph │
│ multi-agent │
│ system │
└───────┬───────┘
│
▼
┌───────────────┐
│ Cohere API │
│ (embed + chat)│
└───────────────┘
**Query flow:** user message → router agent classifies intent (qa / summarize / analyze) → retrieval node fetches relevant chunks (via pgvector cosine similarity, or full-document order for summaries) → specialized agent generates a grounded answer with citations → response streams back to the client → interaction logged to the database.

## Tech Stack

**Backend:** FastAPI, SQLAlchemy (async), Alembic, PostgreSQL + pgvector, LangGraph, Cohere API, slowapi, tiktoken, pypdf, python-docx

**Frontend:** React, Vite, Tailwind CSS, axios, react-router-dom

**Infrastructure:** Docker, Docker Compose, nginx

**Deployment:** Railway (backend + Postgres), Vercel (frontend)

## Getting Started

### Prerequisites

- Docker Desktop
- A [Cohere API key](https://dashboard.cohere.com/api-keys) (free trial tier works)

### Setup

1. Clone the repo:
```bash
   git clone <your-repo-url>
   cd doc-intel
```

2. Create your backend environment file:
```bash
   cp backend/.env.example backend/.env
```
   Then fill in `backend/.env` with:
   - `COHERE_API_KEY` — your Cohere API key
   - `JWT_SECRET_KEY` — generate one with `python -c "import secrets; print(secrets.token_hex(32))"`
   - `POSTGRES_PASSWORD` — any value for local dev (e.g. `docintel`)

3. Run the full stack:
```bash
   docker compose up --build
```

4. Open the app:
   - Frontend: [http://localhost:5173](http://localhost:5173)
   - API docs (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)

5. Register an account, upload a PDF/DOCX/TXT file, and start asking questions in the Chat tab.

## Design Decisions

A few choices worth calling out, since they involved real tradeoffs:

- **Chunking strategy:** recursive, structure-aware splitting (paragraph → sentence → word boundaries) sized by actual token count via `tiktoken`, rather than naive character-based splitting. This keeps chunks semantically coherent instead of cutting mid-sentence.
- **Summarization retrieval:** similarity search performs poorly against vague instructions like "summarize this document" (the instruction itself doesn't semantically match any content). The summarizer instead fetches chunks in document order when a specific document is selected, trading some latency for dramatically better output coherence.
- **Single LLM provider (Cohere):** used for both embeddings and chat generation, simplifying key management. `LLM_PROVIDER` is set up as a config value so swapping providers later wouldn't require touching business logic.
- **Full-text citations:** citations return the complete matched chunk (not a short excerpt), prioritizing transparency over compactness.
- **Separate frontend/backend hosting:** the frontend deploys to Vercel (static CDN) and the backend+DB to Railway (stateful services), mirroring how production systems are typically architected rather than co-locating everything on one server.

## Known Limitations & Future Improvements

- **Chunking:** currently recursive/token-aware; a hierarchical (parent-child) chunking strategy — embedding small chunks for precise retrieval while returning their larger parent chunk for generation context — would likely improve answer quality further.
- **QA route on vague queries:** questions that aren't really questions (e.g. "explain the pdf") still use similarity search and can retrieve loosely-relevant chunks. The summarize route already handles the common "give me an overview" case; a broader fix would detect this pattern for the QA route too.
- **No test suite yet.** Manual end-to-end testing was used throughout development; adding `pytest` coverage for the API and `vitest`/RTL for the frontend would be a natural next step.

## Project Structure

doc-intel/
├── backend/
│ ├── app/
│ │ ├── agents/ # LangGraph multi-agent system
│ │ ├── api/routers/ # auth, documents, chat, health
│ │ ├── core/ # config, security, logging
│ │ ├── db/ # async session, declarative base
│ │ ├── models/ # SQLAlchemy models
│ │ ├── schemas/ # Pydantic request/response models
│ │ └── services/ # ingestion, embeddings
│ ├── alembic/ # database migrations
│ └── Dockerfile
├── frontend/
│ ├── src/
│ │ ├── api/ # axios client, endpoint wrappers
│ │ ├── components/ # ProtectedRoute
│ │ ├── context/ # AuthContext
│ │ └── pages/ # Login, Register, Documents, Chat
│ ├── nginx.conf
│ └── Dockerfile
└── docker-compose.yml

## License

MIT