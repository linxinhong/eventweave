.PHONY: help install test lint typecheck check clean demo-stack golden-check golden-update

help:
	@echo "Available commands:"
	@echo "  make install       Install development dependencies"
	@echo "  make test          Run pytest"
	@echo "  make lint          Run ruff check"
	@echo "  make typecheck     Run mypy"
	@echo "  make check         Run lint + typecheck + test"
	@echo "  make golden-check  Run golden baseline snapshot tests"
	@echo "  make golden-update Regenerate golden baseline files"
	@echo "  make demo-stack    Start the local observability demo stack"
	@echo "  make clean         Remove build artifacts and cache files"

demo-stack:
	examples/demo-stack/run_demo.sh

install:
	uv pip install -e ".[dev]"

test:
	pytest -q

lint:
	ruff check eventweave tests

typecheck:
	mypy eventweave

check: lint typecheck test

golden-check:
	uv run pytest tests/test_golden.py -q

golden-update:
	uv run python scripts/update_golden.py

clean:
	rm -rf dist out .pytest_cache .mypy_cache .ruff_cache __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name '*.egg-info' -exec rm -rf {} +
