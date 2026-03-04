# Twype Voice

Interactive AI agent for expert consultations (medicine, psychology, nutrition). Voice + text via LiveKit, RAG with source attribution, emotional adaptation using the Circumplex model.

## Architecture

7 Docker containers on a single VPS, orchestrated via Docker Compose.

| Container  | Technology               | Role                                             |
| ---------- | ------------------------ | ------------------------------------------------ |
| `api`      | FastAPI (Python)         | REST API: auth, LiveKit tokens, history, sources |
| `agent`    | LiveKit Agents (Python)  | Voice pipeline: VAD → STT → LLM → TTS           |
| `web`      | React PWA (Vite)         | Client: LiveKit Client SDK + HTTP                |
| `livekit`  | LiveKit Server (Go)      | SFU media server, data channels                  |
| `litellm`  | LiteLLM Proxy            | OpenAI-compatible LLM gateway                    |
| `postgres` | PostgreSQL 18 + pgvector | All data + RAG embeddings                        |
| `caddy`    | Caddy 2                  | Reverse proxy + auto SSL                         |
| `coturn`   | coturn                   | TURN server for NAT traversal                    |

### Data Flows

- **Voice:** Client → WebRTC → LiveKit → Agent (Silero VAD → Deepgram STT → LiteLLM/Gemini → Inworld TTS) → Client
- **Text:** Client → LiveKit data channel → Agent → LLM → Client
- **REST:** Client → Caddy → FastAPI → PostgreSQL

## Tech Stack

| Technology             | Minimum Version |
| ---------------------- | --------------- |
| Python                 | 3.13+           |
| uv                     | 0.10.7+         |
| Bun                    | 1.3+            |
| PostgreSQL + pgvector  | 18.2+           |
| Docker Engine          | 27+             |
| Docker Compose         | 2.30+           |

## Project Structure

```
apps/api/          — FastAPI REST API (Python, uv)
apps/agent/        — LiveKit Agent voice pipeline (Python, uv)
apps/web/          — React PWA (Bun, Vite)
packages/shared/   — shared types (optional)
docker/            — Dockerfiles + docker-compose.yml / docker-compose.dev.yml
configs/           — livekit.yaml, litellm.yaml, Caddyfile, turnserver.conf
scripts/           — seed.py, ingest.py, migrate.sh
docs/              — project documentation
```

## Quick Start

```bash
git clone <repo-url> && cd twype-voice
cp .env.example .env   # fill in secrets
make install            # install dependencies (uv + bun)
make dev                # start dev environment
```

## Make Commands

| Command          | Description                              |
| ---------------- | ---------------------------------------- |
| `make help`      | Show help                                |
| `make install`   | Install dependencies (uv + bun)          |
| `make dev`       | Start dev environment (docker compose)   |
| `make up`        | Start production (detached)              |
| `make down`      | Stop all containers                      |
| `make logs`      | Follow container logs                    |
| `make lint`      | Run all linters (ruff + eslint)          |
| `make lint-py`   | Python linter (ruff)                     |
| `make lint-web`  | Frontend linter (eslint)                 |
| `make format`    | Format all code                          |
| `make format-py` | Format Python (ruff)                     |
| `make format-web`| Format frontend (prettier)               |
| `make test`      | Run all tests                            |
| `make test-api`  | API tests (pytest)                       |
| `make test-agent`| Agent tests (pytest)                     |
| `make test-web`  | Frontend tests (vitest)                  |
| `make clean`     | Remove caches and build artifacts        |

## Environment Variables

Defined in `.env` (never committed). Template: `.env.example`.

**API:**
`DATABASE_URL`, `JWT_SECRET`, `RESEND_API_KEY`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `LIVEKIT_URL`

**Agent:**
`LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `LIVEKIT_URL`, `LITELLM_URL`, `DATABASE_URL`, `DEEPGRAM_API_KEY`, `INWORLD_API_KEY`, `ELEVENLABS_API_KEY`

**LiteLLM:**
`GOOGLE_API_KEY`, `OPENAI_API_KEY`

**coturn:**
`TURN_USERNAME`, `TURN_PASSWORD`

## Documentation

- [docs/about.md](docs/about.md) — product description, concepts, MVP scope
- [docs/architecture.md](docs/architecture.md) — system architecture, diagrams
- [docs/specs.md](docs/specs.md) — tech stack, structure, conventions, DB schema
- [docs/plan.md](docs/plan.md) — implementation plan (S01–S25)
