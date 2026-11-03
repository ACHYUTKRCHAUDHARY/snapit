.PHONY: install test lint typecheck imports check

install:
	uv sync --extra dev

test:
	uv run pytest

lint:
	uv run ruff check .

typecheck:
	uv run mypy src

imports:
	uv run lint-imports

check: lint typecheck imports test
