PYTHON_FILES=.

lint format: PYTHON_FILES=.
lint_diff format_diff: PYTHON_FILES=$(shell git diff --name-only --diff-filter=d main | grep -E '\.py$$|\.ipynb$$')

lint lint_diff:
	uv run mypy $(PYTHON_FILES)
	uv run black $(PYTHON_FILES) --check
	uv run ruff $(PYTHON_FILES)

format format_diff:
	uv run black $(PYTHON_FILES)
	uv run ruff check --select I --fix $(PYTHON_FILES)

init:
	docker compose pull

run:
	docker compose up -d db
	uv run fastapi dev main.py

run-mock:
	docker compose up -d db
	uv run mock_obd.py