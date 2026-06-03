# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Vector** is a job board RAG system — a full-stack web app that scrapes LinkedIn jobs, embeds them into ChromaDB for semantic search, and uses multi-agent AI (Claude + LangGraph) to help users find and apply to jobs.

## Commands

### Frontend (`/client`)
```bash
npm run dev        # Start Vite dev server on port 5173
npm run build      # Type-check and bundle
npm run preview    # Serve production build
```

### Backend
```bash
PYTHONPATH=. .venv/bin/python server/main.py   # Start FastAPI server
```

### Full stack
```bash
docker-compose up   # PostgreSQL + Airflow + FastAPI + Ollama
```

### Tests
```bash
PYTHONPATH=. .venv/bin/pytest server/tests/    # Run backend tests
```

## Architecture

### Data flow
1. **Scraping:** Airflow DAG → Selenium scrapes LinkedIn → raw job stubs
2. **Extraction:** LLM parses descriptions → structured fields (skills, seniority, requirements)
3. **Storage:** PostgreSQL (structured) + ChromaDB (embeddings via Ollama `qwen2.5:7b`)
4. **User queries:** React → FastAPI → Orchestrator agent → specialist agents → tools → DB

### Backend (`/server`)

- **`features/`** — FastAPI routers, one subdirectory per domain: `auth/`, `jobs/`, `resumes/`, `applications/`, `agents/`, `stats/`
- **`db/postgres.py`** — All SQL operations (users, jobs, resumes, applications)
- **`db/chroma.py`** — Vector search against ChromaDB
- **`db/embeddings.py`** — Embedding generation via Ollama
- **`agents/`** — Multi-agent orchestration via LangGraph `StateGraph`
- **`pipeline/`** — Scrape → extract → insert → embed workflow
- **`dags/`** — Airflow DAG definitions

### Agent system (`/server/agents`)

The orchestrator (`orchestrator.py`) classifies user intent and routes to one of four specialist agents, each exposed as a `@tool`:
- `db_agent.py` — structured DB queries for job search and stats
- `resume_agent.py` — resume upload, tailoring, gap analysis
- `job_advisor_agent.py` — job recommendations
- `evaluator_agent.py` — candidate-job fit scoring

`conversation_history` is shared across agents as a `ContextVar` (no threading needed). Agent system prompts live in `prompts.py`.

### Frontend (`/client/src`)

React 18 + TypeScript + Vite. Routes are protected via OAuth token handling. Key components: `AgentChat` (streaming agent responses), `ProtectedRoute`. API calls go through Axios to the FastAPI backend.

### Configuration

All secrets and model names are in `.env` (copy from `.env.example`): PostgreSQL connection, Anthropic API key, Ollama endpoint/model, ChromaDB settings.
