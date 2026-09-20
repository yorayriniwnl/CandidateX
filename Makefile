ifeq ($(OS),Windows_NT)
PYTHON := services/backend/.venv/Scripts/python.exe
else
PYTHON := services/backend/.venv/bin/python
endif

.PHONY: help install setup verify test test-backend test-contracts test-db migrate lint build-web dev-backend dev-web

help:
	@echo "Available commands:"
	@echo "  make install         Install backend and frontend dependencies"
	@echo "  make setup           Bootstrap the managed Python environment and browser"
	@echo "  make verify          Run the complete local release gate"
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
	$(PYTHON) -m pip install -e "services/backend[dev]"
	pnpm install

setup:
	powershell -ExecutionPolicy Bypass -File scripts/setup.ps1

verify:
	powershell -ExecutionPolicy Bypass -File scripts/verify.ps1

test: test-backend test-contracts test-db

test-backend:
	$(PYTHON) -m pytest services/backend/tests -v

test-contracts:
	$(PYTHON) -m pytest services/backend/tests/unit/test_contracts.py -v

test-db:
	$(PYTHON) -m pytest services/backend/tests/integration/test_db_migration.py -v

migrate:
	$(PYTHON) -m alembic -c services/backend/alembic.ini upgrade head

lint:
	$(PYTHON) -m pytest --version
	pnpm --filter web lint

build-web:
	pnpm --filter web build

dev-backend:
	$(PYTHON) -m uvicorn cci.main:app --app-dir services/backend/src --reload --port 8000

dev-web:
	pnpm --filter web dev
