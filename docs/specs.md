# Project Technical Specifications

**Version:** 1.0 — MVP
**Date:** March 2026

> This document defines the technology stack, tool versions, project structure, and development practices. Product description — in `docs/about.md`, architecture — in `docs/architecture.md`.

---

## 1. Version Rule

**Downgrading dependency versions below the specified minimums is prohibited.**

Versions listed in this document are the minimum acceptable versions. Upgrading is allowed and encouraged. Downgrading is allowed **only** with a documented technical justification and explicit approval.

This rule applies to:
- Runtime environments (Python, Bun, PostgreSQL)
- All Python and Bun dependencies
- Docker images
- Toolchain (uv, Vite, etc.)

When adding a new dependency, it must be recorded in this document with its minimum version.

---

## 2. Monorepo Structure

The project is organized as a monorepo — frontend, backend API, and agent live in one repository.

```
twype-voice/
├── apps/
│   ├── api/              # FastAPI REST API
│   │   ├── src/
│   │   │   ├── auth/     # Authentication, JWT
│   │   │   ├── routes/   # HTTP endpoints
│   │   │   ├── models/   # SQLAlchemy models
│   │   │   ├── schemas/  # Pydantic schemas
│   │   │   ├── services/ # Business logic
│   │   │   └── main.py   # FastAPI entry point
│   │   ├── migrations/   # Alembic migrations
│   │   ├── tests/
│   │   └── pyproject.toml
│   │
│   ├── agent/            # LiveKit Agent (voice pipeline)
│   │   ├── src/
│   │   │   ├── plugins/  # Custom plugins (Inworld TTS)
│   │   │   ├── prompts/  # Prompt loading from DB
│   │   │   ├── rag/      # RAG search, embeddings
│   │   │   ├── emotions/ # Circumplex model
│   │   │   └── main.py   # Agent entry point
│   │   ├── tests/
│   │   └── pyproject.toml
│   │
│   └── web/              # React PWA
│       ├── src/
│       │   ├── components/
│       │   ├── hooks/
│       │   ├── pages/
│       │   ├── lib/      # Utilities, API client
│       │   └── main.tsx
│       ├── public/
│       ├── tests/
│       ├── package.json
│       ├── tsconfig.json
│       └── vite.config.ts
│
├── packages/
│   └── shared/           # Shared types, constants (optional)
│
├── docker/
│   ├── Dockerfile.api
│   ├── Dockerfile.agent
│   └── Dockerfile.web
│
├── compose.yaml          # Development Docker Compose entrypoint
├── compose.prod.yaml     # Production Docker Compose entrypoint
│
├── configs/
│   ├── livekit.yaml      # LiveKit Server configuration
│   ├── litellm.yaml      # LiteLLM Proxy configuration
│   ├── caddy/Caddyfile   # Caddy configuration
│   └── coturn/turnserver.conf
│
├── scripts/
│   ├── seed.py           # Initial data (prompts, agent configuration)
│   ├── ingest.py         # Loading materials into RAG
│   └── migrate.sh        # Wrapper for running migrations
│
├── docs/
│   ├── about.md          # Product description
│   ├── architecture.md   # System architecture
│   ├── specs.md          # Technical specifications (this file)
│   └── plans/            # Design documents
│
├── .env.example          # Environment variables template
├── pyproject.toml        # Root Python workspace (uv)
├── package.json          # Root Node workspace
└── README.md
```

### Organization Principles

- **apps/** — standalone applications, each built into a separate Docker image
- **packages/** — shared code (used if common types emerge between api and agent)
- **configs/** — configuration files for infrastructure containers (mounted as volumes)
- **scripts/** — utilities not part of application runtime
- **Python workspace** via uv — `apps/api` and `apps/agent` are managed from the root `pyproject.toml`
- **Bun workspace** — `apps/web` is managed from the root `package.json`

---

## 3. Runtime and Toolchain

| Tool | Minimum Version | Purpose |
|---|---|---|
| Python | 3.13.12+ | Runtime for API and Agent |
| uv | 0.10.7+ | Python package and virtual environment manager |
| Bun | 1.3+ | Runtime, package manager, test runner for frontend |
| PostgreSQL | 18.2+ | Primary DB + pgvector |
| Docker Engine | 27+ | Containerization |
| Docker Compose | 2.30+ | Container orchestration |

### Why uv Instead of pip/poetry

- Dependency installation and resolution is orders of magnitude faster
- Single tool: venv creation, package installation, script execution, workspace management
- Lockfile support (`uv.lock`) for reproducible builds
- Compatible with pyproject.toml (PEP 621)

### Why Python 3.13, Not 3.14

Python 3.14 is the current release, but some C extensions (asyncpg, pgvector, Silero) may not have prebuilt wheels for 3.14. Python 3.13 is a stable version with full support for all project dependencies.

---

## 4. Backend — Python Dependencies

### apps/api (FastAPI REST API)

| Package | Minimum Version | Purpose |
|---|---|---|
| fastapi | 0.135.1+ | HTTP framework |
| uvicorn | 0.41.0+ | ASGI server |
| pydantic | 2.12.5+ | Data validation, schemas |
| sqlalchemy | 2.0.48+ | ORM (async mode) |
| alembic | 1.18.4+ | DB migrations |
| asyncpg | 0.31.0+ | Async PostgreSQL driver |
| pgvector | 0.4.2+ | pgvector integration with SQLAlchemy |
| python-jose | 3.4+ | JWT tokens (access/refresh) |
| passlib[bcrypt] | 1.7.4+ | Password hashing |
| resend | 2.7+ | Email sending (registration confirmation) |
| python-multipart | 0.0.20+ | Form-data processing (FastAPI) |
| httpx | 0.28+ | HTTP client (for tests and external requests) |

### apps/agent (LiveKit Agent)

| Package | Minimum Version | Purpose |
|---|---|---|
| livekit-agents | 1.4.4+ | Voice agent framework |
| livekit-plugins-deepgram | 1.4.2+ | Deepgram STT plugin |
| livekit-plugins-silero | 1.3.12+ | VAD (Voice Activity Detection) |
| livekit-plugins-openai | 1.4.2+ | OpenAI-compatible LLM plugin (for LiteLLM) |
| litellm | 1.82.0+ | LLM Proxy SDK (for direct calls, if needed) |
| sqlalchemy | 2.0.48+ | ORM (DB access from agent) |
| asyncpg | 0.31.0+ | Async PostgreSQL driver |
| pgvector | 0.4.2+ | Vector operations |
| pydantic | 2.12.5+ | Data validation |

### Shared Python Dependencies (workspace level)

| Package | Minimum Version | Purpose |
|---|---|---|
| ruff | 0.11+ | Linting + formatting |
| pytest | 8.3+ | Testing |
| pytest-asyncio | 0.26+ | Async tests |

---

## 5. Frontend — Node Dependencies

### apps/web (React PWA)

| Package | Minimum Version | Purpose |
|---|---|---|
| react | 19.2.4+ | UI framework |
| react-dom | 19.2.4+ | React DOM renderer |
| typescript | 5.8+ | Type checking |
| vite | 7.3.1+ | Build tool and dev server |
| livekit-client | 2.17.2+ | LiveKit Client SDK |
| @livekit/components-react | 2.9.20+ | LiveKit React components |
| @tanstack/react-query | 5.75+ | Data fetching for REST API |
| react-router | 7.5+ | Routing |

### LiveKit Agents UI

Agents UI components are installed via the shadcn CLI and copied into the project source code (they are not a dependency):

```bash
bunx shadcn@latest registry add @agents-ui
bunx shadcn@latest add @agents-ui/agent-control-bar
bunx shadcn@latest add @agents-ui/agent-chat-transcript
bunx shadcn@latest add @agents-ui/agent-audio-visualizer-bar
```

Key components:
- `AgentControlBar` — microphone control, muting
- `AgentChatTranscript` — text chat feed with transcripts
- `AgentAudioVisualizerBar` / `Wave` / `Aura` — audio visualization
- `AgentChatIndicator` — agent state indicator

### Frontend Dev Dependencies

| Package | Minimum Version | Purpose |
|---|---|---|
| vitest | 3.2+ | Testing |
| @testing-library/react | 16.3+ | React component testing |
| eslint | 9.22+ | Linting (flat config) |
| prettier | 3.5+ | Formatting |
| @vitejs/plugin-react | 4.4+ | React plugin for Vite |

---

## 6. Authentication (MVP)

### Approach

For MVP — **email + password** with email confirmation. No OAuth, no SSO, no third-party providers.

### Registration Flow

1. User enters email + password
2. API creates a record in the DB with `is_verified = false`
3. API sends an email with a 6-digit confirmation code via Resend
4. User enters the code in the application
5. API verifies the code, sets `is_verified = true`
6. User receives JWT tokens

### JWT Tokens

- **Access token** — short-lived (15 minutes), passed in the `Authorization: Bearer <token>` header
- **Refresh token** — long-lived (30 days), used to renew the access token
- Algorithm: HS256 with a secret from an environment variable

### LiveKit Token

After JWT validation, the client requests a LiveKit token from the API for room connection. The API generates the token via the `livekit-api` Python SDK with permissions defined for the given user.

### Password Hashing

bcrypt via passlib. Minimum password length — 8 characters.

### Resend

Service for sending transactional emails. Used only for registration confirmation (MVP). The API key is passed via the `RESEND_API_KEY` environment variable.

---

## 7. Database and Migrations

### SQLAlchemy 2.0

- **Async mode** via asyncpg
- **Mapped columns** (Mapped[type] instead of Column(Type))
- **Type annotations** in all models
- Sessions via async context manager

```python
# Model declaration style
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_verified: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

### Naming Conventions

- Tables: **snake_case, plural** (`users`, `sessions`, `messages`, `knowledge_chunks`)
- Columns: **snake_case** (`created_at`, `source_type`, `embedding_vector`)
- Indexes: `ix_{table}_{column}` (automatically via SQLAlchemy naming convention)
- Foreign keys: `fk_{table}_{column}_{ref_table}`
- Constraints: `ck_{table}_{description}`

### Alembic

- Migrations are stored in `apps/api/migrations/`
- Migration autogeneration: `alembic revision --autogenerate -m "description"`
- All migrations are **forward-only** for MVP (downgrade is not required)
- Migrations run before the api container starts

### pgvector

- Extension is enabled via migration: `CREATE EXTENSION IF NOT EXISTS vector`
- Embedding columns: `Vector(dim)` type via pgvector SQLAlchemy integration
- HNSW indexes for ANN search
- Embedding dimensionality is determined by the chosen embedding model (fixed when the first materials are loaded)

---

## 8. Linting and Code Style

### Python — Ruff

Ruff is used for both linting and formatting (replacing flake8, black, isort).

```toml
# pyproject.toml (root)
[tool.ruff]
target-version = "py313"
line-length = 100

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "N",    # pep8-naming
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "SIM",  # flake8-simplify
    "ASYNC",# flake8-async
    "S",    # flake8-bandit (security)
    "T20",  # flake8-print
    "RUF",  # ruff-specific
]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101"]  # assert is acceptable in tests

[tool.ruff.format]
quote-style = "double"
```

### Frontend — ESLint + Prettier

ESLint 9+ with flat config. Prettier for formatting.

```js
// eslint.config.js (template)
import eslint from "@eslint/js";
import tseslint from "typescript-eslint";
import reactPlugin from "eslint-plugin-react";
import hooksPlugin from "eslint-plugin-react-hooks";

export default tseslint.config(
  eslint.configs.recommended,
  ...tseslint.configs.strictTypeChecked,
  {
    plugins: { react: reactPlugin, "react-hooks": hooksPlugin },
    rules: {
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
    },
  }
);
```

### TypeScript — Strict Mode

```json
// tsconfig.json (key options)
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true,
    "exactOptionalPropertyTypes": true,
    "moduleResolution": "bundler",
    "target": "ES2024",
    "lib": ["ES2024", "DOM", "DOM.Iterable"]
  }
}
```

### Pre-commit Hooks

Pre-commit checks (via `lefthook`):
- `ruff check` + `ruff format --check` for Python
- `bunx eslint .` + `bunx prettier --check .` for TypeScript
- `bunx tsc --noEmit` for type checking

---

## 9. Testing (MVP)

### Backend — pytest

| Tool | Purpose |
|---|---|
| pytest | Test framework |
| pytest-asyncio | Async tests |
| httpx | Async HTTP client for FastAPI tests |

What is tested in MVP:
- **API endpoints** — each endpoint is covered by at least one happy-path test
- **Authentication** — registration, login, refresh, email verification
- **Critical services** — LiveKit token generation, source retrieval

What is NOT tested in MVP:
- LiveKit Agent (voice pipeline) — tested manually via Agents Playground
- Integration with external APIs (Deepgram, Inworld, LLM providers)
- e2e scenarios

```python
# Test structure
apps/api/tests/
├── conftest.py          # Fixtures (test client, test DB)
├── test_auth.py         # Registration, login, JWT
├── test_sessions.py     # Session history
└── test_sources.py      # RAG source metadata
```

### Frontend — Vitest

| Tool | Purpose |
|---|---|
| vitest | Test framework (Vite integration) |
| @testing-library/react | React component testing |

What is tested in MVP:
- **Utilities** — formatting, parsing, helpers
- **Key components** — rendering, user events

---

## 10. Docker Development

### Production (compose.prod.yaml)

Full stack of 7 containers (described in `docs/architecture.md`, section 1). Images are built multi-stage, minimal size.

### Development (compose.yaml)

Differences from production:
- **apps/api** — source volume mount, uvicorn with `--reload`
- **apps/agent** — source volume mount, LiveKit Agent in `dev` mode (auto-reload)
- **apps/web** — source volume mount, Vite dev server with HMR
- **postgres** — same image, but with dev data (seed)
- **livekit/coturn/litellm/caddy** — identical to production

```yaml
# compose.yaml (schematic)
services:
  api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
      target: dev
    volumes:
      - ./apps/api/src:/app/src
    command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      - DEBUG=true

  agent:
    build:
      context: .
      dockerfile: docker/Dockerfile.agent
      target: dev
    volumes:
      - ./apps/agent/src:/app/src
    command: python -m livekit.agents dev src/main.py

  web:
    build:
      context: .
      dockerfile: docker/Dockerfile.web
      target: dev
    volumes:
      - ./apps/web/src:/app/src
    ports:
      - "5173:5173"
    command: bunx vite --host
```

### Running

```bash
# Development
docker compose up

# Production
docker compose -f compose.prod.yaml up -d

# Migrations
docker compose exec api alembic upgrade head

# Load initial data
docker compose exec api python scripts/seed.py
```

---

## 11. Environment Variables

All secrets are stored in the `.env` file (never committed). Template — `.env.example`.

### API Container

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_SECRET` | Secret for signing JWT tokens |
| `RESEND_API_KEY` | Resend API key for email |
| `LIVEKIT_API_KEY` | LiveKit API key (for token generation) |
| `LIVEKIT_API_SECRET` | LiveKit API secret |
| `LIVEKIT_URL` | LiveKit Server URL (internal) |
| `GOOGLE_API_KEY` | Google API key for direct Gemini embeddings during ingestion |

### Agent Container

| Variable | Description |
|---|---|
| `LIVEKIT_API_KEY` | LiveKit API key |
| `LIVEKIT_API_SECRET` | LiveKit API secret |
| `LIVEKIT_URL` | LiveKit Server URL (internal) |
| `LITELLM_URL` | LiteLLM Proxy URL (internal) |
| `DATABASE_URL` | PostgreSQL connection string |
| `DEEPGRAM_API_KEY` | Deepgram API key (STT) |
| `INWORLD_API_KEY` | Inworld API key (TTS) |
| `ELEVENLABS_API_KEY` | ElevenLabs API key (fallback TTS) |

### LiteLLM Container

| Variable | Description |
|---|---|
| `GOOGLE_API_KEY` | Google API key (Gemini) |
| `OPENAI_API_KEY` | OpenAI API key (optional fallback LLM) |

### LiveKit Container

Configuration via `configs/livekit.yaml` (API key/secret are set in YAML).

### coturn Container

| Variable | Description |
|---|---|
| `TURN_USERNAME` | TURN username |
| `TURN_PASSWORD` | TURN password |

---

## 12. Git Conventions

### Branching

- `main` — stable branch, deployed to production
- `dev` — integration branch for development
- Feature branches: `feat/short-description`
- Bugfix branches: `fix/short-description`

### Commits

Format: [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

feat(api): add user registration endpoint
fix(agent): handle STT timeout gracefully
chore(docker): update PostgreSQL to 18.3
docs(specs): add testing conventions
```

Types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `style`, `perf`.
Scope: `api`, `agent`, `web`, `docker`, `docs`, `ci`.
