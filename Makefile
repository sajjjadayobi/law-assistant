.PHONY: help install format lint typecheck test coverage clean all

help:
	@echo "Law Agent - Development Commands"
	@echo "================================="
	@echo ""
	@echo "Setup:"
	@echo "  make install       Install project with dev dependencies"
	@echo ""
	@echo "Code Quality:"
	@echo "  make format        Format code with Black"
	@echo "  make lint          Check and fix code with Ruff"
	@echo "  make typecheck     Type check with mypy"
	@echo ""
	@echo "Testing:"
	@echo "  make test          Run all tests"
	@echo "  make coverage      Generate coverage report (HTML)"
	@echo ""
	@echo "Utilities:"
	@echo "  make all           Run format, lint, typecheck, and test"
	@echo "  make clean         Clean build artifacts and cache"

install:
	uv pip install -e ".[dev]"

format:
	@echo "Formatting code with Black..."
	black .

lint:
	@echo "Linting with Ruff..."
	ruff check . --fix

typecheck:
	@echo "Type checking with mypy..."
	mypy src/

test:
	@echo "Running tests..."
	pytest tests/ -v

coverage:
	@echo "Generating coverage report..."
	pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated: htmlcov/index.html"

clean:
	@echo "Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov/ .coverage coverage.xml
	@echo "✓ Cleanup complete"

all: format lint typecheck test
	@echo ""
	@echo "✅ All checks passed!"
