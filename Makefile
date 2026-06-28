.PHONY: help install test lint typecheck check clean

help:
	@echo "Available commands:"
	@echo "  make install    Install development dependencies"
	@echo "  make test       Run pytest"
	@echo "  make lint       Run ruff check"
	@echo "  make typecheck  Run mypy"
	@echo "  make check      Run lint + typecheck + test"
	@echo "  make clean      Remove build artifacts and cache files"

install:
	uv pip install -e ".[dev]"

test:
	pytest -q

lint:
	ruff check eventweave tests

typecheck:
	mypy eventweave

check: lint typecheck test

clean:
	rm -rf dist out .pytest_cache .mypy_cache .ruff_cache __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name '*.egg-info' -exec rm -rf {} +
