.PHONY: format lint typecheck test all clean help

help:
	@echo "Available commands:"
	@echo "  make format     - Format code with Black"
	@echo "  make lint       - Lint code with Ruff"
	@echo "  make typecheck  - Type check with mypy"
	@echo "  make test       - Run tests with pytest"
	@echo "  make all        - Run all checks (format, lint, typecheck, test)"
	@echo "  make clean      - Remove build artifacts and cache files"

format:
	black .

lint:
	ruff check . --fix

typecheck:
	mypy src/

test:
	pytest tests/

all: format lint typecheck test
	@echo "All checks passed!"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov/ .coverage coverage.xml
	@echo "Cleaned up build artifacts and cache files"
