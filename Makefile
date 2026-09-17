.PHONY: help install test test-backend test-contracts test-db migrate lint build-web dev-backend dev-web

help:
	@echo "Available commands:"
	@echo "  make install         Install backend and frontend dependencies"
	@echo "  make test            Run full test suite"
	@echo "  make test-backend    Run all backend pytest tests"
	@echo "  make test-contracts  Run unit tests validating domain contracts and enums"
	@echo "  make test-db         Run database migration smoke tests"
	@echo "  make migrate         Run Alembic database migrations"
	@echo "  make lint            Run linter checks on frontend and backend"
	@echo "  make build-web       Build Next.js web application"
	@echo "  make dev-backend     Start FastAPI backend with reload"
	@echo "  make dev-web         Start Next.js frontend development server"

install:
	python -m pip install -e services/backend
	pnpm install

test: test-backend test-contracts test-db

test-backend:
	python -m pytest services/backend/tests -v

test-contracts:
	python -m pytest services/backend/tests/unit/test_contracts.py -v

test-db:
	python -m pytest services/backend/tests/integration/test_db_migration.py -v

migrate:
	cd services/backend && alembic upgrade head

lint:
	python -m pytest --version
	pnpm --filter web lint

build-web:
	pnpm --filter web build

dev-backend:
	python -m uvicorn cci.main:app --app-dir services/backend/src --reload --port 8000

dev-web:
	pnpm --filter web dev
