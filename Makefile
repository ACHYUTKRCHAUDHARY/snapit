.PHONY: install test lint typecheck imports check

install:
	uv sync

test:
	uv run poe test

lint:
	uv run poe lint

typecheck:
	uv run poe typecheck

imports:
	uv run poe imports

format:
	uv run poe format

check:
	uv run poe check
