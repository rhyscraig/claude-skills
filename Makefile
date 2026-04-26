.PHONY: install test coverage lint format typecheck check clean help

help:
	@echo "Claude Skills Platform - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install           Install development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test              Run all tests"
	@echo "  make coverage          Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make format            Format code with black"
	@echo "  make lint              Lint with ruff"
	@echo "  make typecheck         Type check with mypy"
	@echo "  make check             Run all quality checks"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean             Remove build artifacts"
	@echo "  make help              Show this help message"

install:
	@echo "Installing development dependencies..."
	pip install -e ".[dev]"
	@echo "✅ Installation complete"

test:
	@echo "Running tests..."
	pytest tests/ -v
	@echo "✅ Tests complete"

coverage:
	@echo "Running tests with coverage..."
	pytest tests/ --cov=src --cov-report=html --cov-report=term
	@echo "✅ Coverage report generated (htmlcov/index.html)"

lint:
	@echo "Linting with ruff..."
	ruff check src/ tests/
	@echo "✅ Linting complete"

format:
	@echo "Formatting code with black..."
	black src/ tests/ docs/
	@echo "✅ Formatting complete"

typecheck:
	@echo "Type checking with mypy..."
	mypy src/ --strict --ignore-missing-imports
	@echo "✅ Type checking complete"

check: lint format typecheck test
	@echo "✅ All checks passed!"

clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/ dist/ *.egg-info
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
	rm -rf htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "✅ Cleanup complete"
