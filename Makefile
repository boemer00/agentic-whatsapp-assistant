PYTHON ?= python
PIP ?= pip
RUFF ?= ruff
MYPY ?= mypy

.DEFAULT_GOAL := help

help:
    @echo "make install     - install dev deps into active env"
	@echo "make run         - start dev server (reload)"
	@echo "make lint        - ruff lint"
	@echo "make format      - ruff fix + format"
	@echo "make typecheck   - mypy"
	@echo "make docker-up   - run via docker compose"
	@echo "make docker-down - stop containers"
    @echo "make clean       - remove caches"

install:
    $(PYTHON) -m pip install -U pip
    $(PIP) install -r requirements-dev.txt

run:
    APP_ENV=dev LOG_LEVEL=DEBUG $(PYTHON) -m uvicorn src.main:app --reload --host 0.0.0.0 --port $${PORT:-8000}

lint:
    $(RUFF) check src

format:
	$(RUFF) check --fix src
	$(RUFF) format src

typecheck:
    $(MYPY) --package src

docker-up:
	docker compose up --build

docker-down:
	docker compose down

clean:
    rm -rf __pycache__ .pytest_cache .mypy_cache
