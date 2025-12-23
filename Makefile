.PHONY: test lint bench format

lint:
	uv run ruff check uj0e scripts tests
	uv run black --check uj0e scripts tests

format:
	uv run ruff check --fix uj0e scripts tests
	uv run black uj0e scripts tests

test:
	uv run pytest -q

bench:
	uv run python scripts/autocorrect_loop.py "dry run benchmark" --max-iters 1
