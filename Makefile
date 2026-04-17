.PHONY: help dev up down build test lint migrate seed

# Always resolve docker compose with the local env file.
# Users should copy docker/.env.docker.example to docker/.env.docker.
COMPOSE := docker compose --env-file docker/.env.docker -f docker/docker-compose.yml

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# === Docker ===

up: ## Start all services
	$(COMPOSE) up -d

down: ## Stop all services
	$(COMPOSE) down

build: ## Build all Docker images
	$(COMPOSE) build

logs: ## Tail logs for all services
	$(COMPOSE) logs -f

logs-api: ## Tail API logs
	$(COMPOSE) logs -f api

logs-worker: ## Tail Celery worker logs
	$(COMPOSE) logs -f celery-worker

# === Backend ===

api-dev: ## Run API server locally (no Docker)
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

api-shell: ## Open shell in API container
	$(COMPOSE) exec api bash

# === Frontend ===

fe-dev: ## Run frontend locally (no Docker)
	cd frontend && npm run dev

fe-install: ## Install frontend dependencies
	cd frontend && npm install

fe-build: ## Build frontend
	cd frontend && npm run build

# === Database ===

migrate: ## Run Alembic migrations
	cd backend && alembic -c alembic/alembic.ini upgrade head

migrate-new: ## Create a new migration (usage: make migrate-new msg="description")
	cd backend && alembic -c alembic/alembic.ini revision --autogenerate -m "$(msg)"

migrate-down: ## Rollback last migration
	cd backend && alembic -c alembic/alembic.ini downgrade -1

db-shell: ## Open psql shell
	$(COMPOSE) exec db psql -U kwgrowth -d kwgrowth

migrate-docker: ## Run Alembic migrations inside the api container
	$(COMPOSE) exec api alembic -c alembic/alembic.ini upgrade head

db-reset: ## DESTRUCTIVE: drop & recreate the dev database (keeps container)
	$(COMPOSE) exec db psql -U kwgrowth -d postgres -c "DROP DATABASE IF EXISTS kwgrowth;"
	$(COMPOSE) exec db psql -U kwgrowth -d postgres -c "CREATE DATABASE kwgrowth OWNER kwgrowth;"
	$(COMPOSE) exec db psql -U kwgrowth -d kwgrowth -f /docker-entrypoint-initdb.d/01-init.sql

# === Testing ===

test: ## Run all backend tests
	cd backend && python -m pytest tests/ -v

test-cov: ## Run tests with coverage
	cd backend && python -m pytest tests/ --cov=app --cov-report=html

test-fe: ## Run frontend tests
	cd frontend && npm test

# === Linting ===

lint: ## Lint backend code
	cd backend && ruff check app/ tests/

lint-fix: ## Fix backend lint issues
	cd backend && ruff check --fix app/ tests/

format: ## Format backend code
	cd backend && ruff format app/ tests/

lint-fe: ## Lint frontend code
	cd frontend && npm run lint

# === Utilities ===

seed: ## Seed database with roles + plans
	cd backend && python -m scripts.seed

seed-demo: ## Seed database with demo company + contacts + deals + conversations
	cd backend && python -m scripts.seed_demo

clean: ## Clean generated files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null; \
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null; \
	rm -rf frontend/.next frontend/out
