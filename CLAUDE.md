# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Twype — interactive AI agent specializing in expert topics (medicine, psychology, etc.). Dual-mode: voice (WebRTC) + text (data channel), both via LiveKit. RAG-powered answers with source attribution. Emotional adaptation via Circumplex model. All documentation in Russian.

**Current state:** architecture and specs complete, no source code yet. Implementation follows `docs/plan.md` (25 sequential stories).

## Project conventions

`docs/` contains human-readable artifacts for understanding and shaping the system.

- `decisions/` — architecture decision records (`NNNN-title.md`)
- `explorations/` — research findings (`YYYY-MM-DD-topic.md`, created by researcher)

`openspec/` is for implementation tracking — structured specs and active changes.

- `specs/` — shaped features with defined behavior
- `changes/` — active implementation work tracked via OpenSpec workflow

All doc edits go through the `tech-writer` agent — never edit documentation files inline. Exceptions: the researcher creates explorations, and the architect owns decision substance.

All non-Markdown project files MUST be written in English only. No other language is allowed
directly in source files. This includes source code, tests, configuration values, default
seed content, user-facing fallback strings, and code comments. `*.md` files are the only
exception.

Any localized or user-facing text that must exist in multiple languages MUST go through the
project translation system instead of being hardcoded in source files.

- Backend: use the backend translation/localization system and locale-aware stored content
  for prompts, generated text templates, emails, and other localized runtime text.
- Frontend: use the frontend translation/localization system for all UI copy and localized
  user-facing text.

Production code MUST follow SOLID, DRY, and KISS. Prefer the simplest design that correctly
implements the current story without duplication, hidden coupling, or speculative abstractions.

Production code MUST NOT contain stubs, mocks, fake implementations, placeholder business logic,
or non-working fallbacks for features that are already implemented or technically possible now.
If a behavior cannot be implemented correctly yet because it depends on a not-yet-completed story
from `docs/plan.md`, add a concise `TODO` that references the blocking story and describes what
remains to be implemented. Do not use `TODO` as a substitute for finishing work that can already
be completed properly.

## Skills & Docs Attribution

Every final report MUST include at the end:

- `Skills used: <list>` — if any skills were consulted
- `Docs used: <list>` — if any external documentation was fetched, on the new line of the report

## Delegation

When delegating to agents, pass raw intent — what needs to happen and why. Don't specify files, formats, or structure. Don't enumerate what to keep, remove, or add — describe the goal and constraints, let the agent decide. Preserve the user's original words and scope. Each agent owns its domain and knows its own guidelines. Micromanaging duplicates their built-in knowledge and risks contradicting it.

## Development workflow

When delegating work to subagents or spawning a team, use the `/team-lead` skill.

### Story planning

When the user asks to "plan the next story" (or similar), find the first unchecked (`- [ ]`) story in `docs/plan.md` and use it as input for `/openspec-new-change`. Stories are sequential — always pick the next one by order, not by topic.

## Documentation

- `docs/about.md` — product description, concepts, MVP scope
- `docs/architecture.md` — system architecture, data flows, sequence diagrams
- `docs/specs.md` — tech stack versions, monorepo structure, coding conventions, DB schema style
- `docs/plan.md` — ordered implementation stories (S01–S25)

**Read specs.md before writing any code** — it defines minimum dependency versions, naming conventions, and project structure.

## Architecture

7 Docker containers on a single VPS, orchestrated via Docker Compose:

| Container  | Tech                     | Role                                             |
| ---------- | ------------------------ | ------------------------------------------------ |
| `api`      | FastAPI (Python)         | REST API: auth, LiveKit tokens, history, sources |
| `agent`    | LiveKit Agents (Python)  | Voice pipeline: VAD → STT → LLM → TTS            |
| `web`      | React PWA (Vite)         | Client: LiveKit Client SDK + HTTP                |
| `livekit`  | LiveKit Server (Go)      | SFU media server, data channels                  |
| `litellm`  | LiteLLM Proxy            | OpenAI-compatible LLM gateway for chat models    |
| `postgres` | PostgreSQL 18 + pgvector | All data + RAG embeddings                        |
| `caddy`    | Caddy 2                  | Reverse proxy + auto SSL                         |
| `coturn`   | coturn                   | TURN server for NAT traversal                    |

Key data flows:

- **Voice:** Client → WebRTC → LiveKit → Agent (Silero VAD → Deepgram STT → LiteLLM-backed LLM → Inworld TTS) → WebRTC → Client
- **Text:** Client → LiveKit data channel → Agent (→ LLM) → data channel → Client
- **REST:** Client → Caddy → FastAPI → PostgreSQL
- **RAG ingestion:** API container → direct Gemini embeddings → PostgreSQL + pgvector

## Monorepo Structure

```
apps/api/          — FastAPI REST API (Python, uv)
apps/agent/        — LiveKit Agent voice pipeline (Python, uv)
apps/web/          — React PWA (Bun)
packages/shared/   — shared types (optional)
docker/            — Dockerfiles
compose.yaml       — development Docker Compose entrypoint (uses root `.env`)
compose.prod.yaml  — production Docker Compose entrypoint (uses root `.env`)
configs/           — livekit.yaml, litellm.yaml, Caddyfile, turnserver.conf
scripts/           — seed.py, ingest.py, migrate.sh
```

Python workspace managed by `uv` from root `pyproject.toml`. Bun workspace from root `package.json`.

## Tech Stack & Versions

All versions in `docs/specs.md` are **minimums** — never downgrade below them.

- **Python 3.13+**, managed by **uv 0.10.7+** (not pip/poetry)
- **Bun 1.3+** (runtime, package manager, test runner for frontend)
- **PostgreSQL 18.2+** with **pgvector** extension
- **Docker Engine 27+**, **Docker Compose 2.30+**

## Commands (planned)

```bash
# Development
docker compose up

# Production
docker compose -f compose.prod.yaml up -d

# Migrations
docker compose exec api alembic upgrade head

# Seed data
docker compose exec api python scripts/seed.py

# Python lint/format
uv run ruff check .
uv run ruff format .

# Python tests
uv run pytest apps/api/tests/
uv run pytest apps/agent/tests/

# Frontend dev
cd apps/web && bun run dev

# Frontend lint/test
cd apps/web && bunx eslint . && bunx prettier --check .
cd apps/web && bunx vitest
```

## Coding Conventions

### Python (api + agent)

- Ruff for linting + formatting (`line-length = 100`, `target-version = "py313"`)
- SQLAlchemy 2.0 async mode with `Mapped[type]` annotations (not `Column(Type)`)
- Tables: snake_case plural (`users`, `messages`). Columns: snake_case
- Index naming: `ix_{table}_{column}`, FK: `fk_{table}_{column}_{ref_table}`
- Alembic migrations: forward-only, autogenerate

### TypeScript (web)

- Strict mode (`strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`)
- ESLint 9+ flat config + Prettier
- React 19+ with LiveKit components via shadcn CLI (@agents-ui)

### Git

- Branches: `main` (production), `dev` (integration), `feat/...`, `fix/...`
- Conventional Commits: `feat(api):`, `fix(agent):`, `chore(docker):` etc.
- Scopes: `api`, `agent`, `web`, `docker`, `docs`, `ci`

## Key Design Principles

- **Provider-agnostic:** STT/LLM/TTS swappable via config. Golden profile: Deepgram + Gemini Flash-Lite + Inworld.
- **Config in DB, not code:** prompts, agent settings, TTS params stored in PostgreSQL. Config snapshot frozen per session.
- **Streaming everywhere:** STT streams words, LLM streams tokens, TTS starts before LLM finishes.
- **All containers via Docker** — no local installs for runtime services.
- **Language-agnostic:** no hardcoded languages. English + Russian on launch, extensible.

## Environment Variables

Defined in `.env` (never committed). Template in `.env.example`. Key groups:

- **API:** `DATABASE_URL`, `JWT_SECRET`, `RESEND_API_KEY`, `LIVEKIT_API_KEY/SECRET/URL`, `GOOGLE_API_KEY`
- **Agent:** `LIVEKIT_*`, `LITELLM_URL`, `DATABASE_URL`, `DEEPGRAM_API_KEY`, `INWORLD_API_KEY`, `ELEVENLABS_API_KEY`
- **LiteLLM:** `GOOGLE_API_KEY`, `OPENAI_API_KEY` (optional additional provider)
- **coturn:** `TURN_USERNAME`, `TURN_PASSWORD`

## Secrets and Blockers

- The single source of truth for runtime secrets is the root `.env`. Do not create or rely on a second `.env`.
- If a required key is missing, empty, placeholder-looking, or rejected by the provider, treat this as a hard blocker.
- In blocker cases, stop further implementation or integration work that depends on that provider and ask the user for a valid key.
- Do not keep coding around invalid credentials, add fake fallbacks, or mark provider-dependent verification as complete.
