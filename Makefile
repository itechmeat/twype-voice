.DEFAULT_GOAL := help

.PHONY: help install dev dev-up up down logs lint lint-py lint-web format format-py format-web \
        test test-api test-agent test-web clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install all dependencies (uv + bun)
	uv sync
	cd apps/web && bun install

dev: ## Start development environment (foreground, shows logs)
	docker compose --env-file .env -f docker/docker-compose.dev.yml up

dev-up: ## Start development environment (detached)
	docker compose --env-file .env -f docker/docker-compose.dev.yml up -d

up: ## Start production environment (docker compose, detached)
	docker compose --env-file .env -f docker/docker-compose.yml up -d

down: ## Stop all containers
	docker compose --env-file .env -f docker/docker-compose.dev.yml down 2>/dev/null; \
	docker compose --env-file .env -f docker/docker-compose.yml down 2>/dev/null; \
	true

logs: ## Follow container logs
	docker compose --env-file .env -f docker/docker-compose.dev.yml logs -f

# ---------------------------------------------------------------------------
# Lint
# ---------------------------------------------------------------------------

lint: lint-py lint-web ## Run all linters

lint-py: ## Run Python linter (ruff)
	uv run ruff check .

lint-web: ## Run frontend linter (eslint)
	cd apps/web && bunx eslint .

# ---------------------------------------------------------------------------
# Format
# ---------------------------------------------------------------------------

format: format-py format-web ## Format all code

format-py: ## Format Python code (ruff)
	uv run ruff format .

format-web: ## Format frontend code (prettier)
	cd apps/web && bunx prettier --write .

# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

test: test-api test-agent test-web ## Run all tests

test-api: ## Run API tests (pytest)
	uv run pytest apps/api/tests/ -v

test-agent: ## Run agent tests (pytest)
	uv run pytest apps/agent/tests/ -v

test-web: ## Run frontend tests (vitest)
	cd apps/web && bunx vitest run

# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------

clean: ## Remove caches and build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null; true
	rm -rf apps/web/dist apps/web/node_modules/.vite
