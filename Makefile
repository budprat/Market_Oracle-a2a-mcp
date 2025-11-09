.PHONY: help install test test-unit test-integration test-all coverage lint format clean

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	uv sync --all-extras

install-dev:  ## Install development dependencies
	uv sync --all-extras
	uv add --dev ruff mypy

test:  ## Run all non-slow tests
	uv run pytest tests/ -v -m "not slow"

test-unit:  ## Run only unit tests
	uv run pytest tests/unit -v -m "unit"

test-integration:  ## Run only integration tests (excluding slow tests)
	uv run pytest tests/integration -v -m "integration and not slow"

test-all:  ## Run all tests including slow tests
	uv run pytest tests/ -v

test-watch:  ## Run tests in watch mode
	uv run pytest-watch tests/ -v

coverage:  ## Run tests with coverage report
	uv run pytest tests/ -v \
		--cov=src/a2a_mcp \
		--cov-report=html \
		--cov-report=term-missing \
		--cov-fail-under=70 \
		-m "not slow"
	@echo "\nCoverage report generated in htmlcov/index.html"

coverage-open:  ## Run coverage and open report in browser
	make coverage
	@python -m webbrowser htmlcov/index.html 2>/dev/null || open htmlcov/index.html || xdg-open htmlcov/index.html

lint:  ## Run linting checks
	uv run ruff check src/ tests/

lint-fix:  ## Fix linting issues automatically
	uv run ruff check --fix src/ tests/

format:  ## Format code with ruff
	uv run ruff format src/ tests/

format-check:  ## Check code formatting
	uv run ruff format --check src/ tests/

type-check:  ## Run type checking with mypy
	uv run mypy src/a2a_mcp --ignore-missing-imports

clean:  ## Clean up generated files
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .ruff_cache
	rm -rf .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.db" -delete

test-verbose:  ## Run tests with verbose output and logging
	uv run pytest tests/ -v -s --log-cli-level=INFO -m "not slow"

test-failed:  ## Re-run only failed tests
	uv run pytest tests/ -v --lf

test-parallel:  ## Run tests in parallel
	uv run pytest tests/ -v -n auto -m "not slow"

ci:  ## Run CI checks locally
	make lint
	make format-check
	make test
	make coverage

init-db:  ## Initialize test database
	python init_database.py

start-mcp:  ## Start MCP server for testing
	./run_mcp_server.sh

check:  ## Run all checks (lint, format, type, test)
	@echo "Running all checks..."
	@make lint
	@make format-check
	@make type-check
	@make test
	@echo "\n✅ All checks passed!"
