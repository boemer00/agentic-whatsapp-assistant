PYTHON := python3
VENV := .venv
PIP := $(VENV)/bin/pip
PY := $(VENV)/bin/python
RUFF := $(VENV)/bin/ruff
MYPY := $(VENV)/bin/mypy

.DEFAULT_GOAL := help

help:
	@echo "make install     - create venv and install deps"
	@echo "make run         - start dev server (reload)"
	@echo "make lint        - ruff lint"
	@echo "make format      - ruff fix + format"
	@echo "make typecheck   - mypy"
	@echo "make docker-up   - run via docker compose"
	@echo "make docker-down - stop containers"
	@echo "make clean       - remove caches/venv"

install:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install -U pip
	$(PIP) install -r requirements-dev.txt

run:
	APP_ENV=dev LOG_LEVEL=DEBUG $(PY) -m uvicorn src.main:app --reload --host 0.0.0.0 --port $${PORT:-8000}

lint: $(RUFF)
	$(RUFF) check src

format:
	$(RUFF) check --fix src
	$(RUFF) format src

typecheck: $(MYPY)
	$(MYPY) --package src

docker-up:
	docker compose up --build

docker-down:
	docker compose down

clean:
	rm -rf .venv __pycache__ .pytest_cache .mypy_cache
