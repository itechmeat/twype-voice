.DEFAULT_GOAL := help

.PHONY: help install dev up down logs lint format test clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install all dependencies (uv + bun)
	uv sync
	cd apps/web && bun install

dev: ## Start development environment (docker compose)
	docker compose --env-file .env -f docker/docker-compose.dev.yml up

up: ## Start production environment (docker compose, detached)
	docker compose --env-file .env -f docker/docker-compose.yml up -d

down: ## Stop all containers
	docker compose --env-file .env -f docker/docker-compose.dev.yml down 2>/dev/null; \
	docker compose --env-file .env -f docker/docker-compose.yml down 2>/dev/null; \
	true

logs: ## Follow container logs
	docker compose --env-file .env -f docker/docker-compose.dev.yml logs -f

lint: ## Run linters (ruff + eslint)
	uv run ruff check .
	cd apps/web && bunx eslint .

format: ## Format code (ruff + prettier)
	uv run ruff format .
	cd apps/web && bunx prettier --write .

test: ## Run tests (pytest + vitest)
	uv run pytest apps/api/tests/ apps/agent/tests/
	cd apps/web && bunx vitest run

clean: ## Remove caches and build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null; true
	rm -rf apps/web/dist apps/web/node_modules/.vite
