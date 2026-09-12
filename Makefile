.PHONY: help install migrate seed api web verify embed-check test lint

help:
	@echo "install      install backend + frontend dependencies"
	@echo "migrate      apply both SQL migrations to \$$DATABASE_URL"
	@echo "seed         load data/grants_seed.csv into the grants table"
	@echo "api          run the FastAPI backend on :8000"
	@echo "web          run the Vite frontend on :5173"
	@echo "verify       Phase 0 acceptance check"
	@echo "embed-check  BGE-M3 throughput on this machine"
	@echo "test         backend tests"
	@echo "lint         ruff check"

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

migrate:
	psql "$$DATABASE_URL" -f backend/migrations/0001_init.sql
	psql "$$DATABASE_URL" -f backend/migrations/0002_rls.sql

seed:
	cd backend && python -m scripts.seed_grants

api:
	cd backend && uvicorn app.main:app --reload --port 8000

web:
	cd frontend && npm run dev

verify:
	cd backend && python -m scripts.verify_setup

embed-check:
	cd backend && python -m scripts.check_embedding_compute

test:
	cd backend && pytest -q

lint:
	cd backend && ruff check app scripts tests
