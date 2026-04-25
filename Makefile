# ==============================================================================
# Claude Skills — Master Makefile
# ==============================================================================

PYTHON := python3
PIP := $(PYTHON) -m pip
PYTEST := pytest
RUFF := ruff
BLACK := black
MYPY := mypy
BANDIT := bandit
POETRY := poetry

.PHONY: help install bootstrap check lint format security test coverage clean build publish

help:
	@echo "Claude Skills Development Workflow"
	@echo "===================================="
	@echo "make install       : Install package in editable mode"
	@echo "make bootstrap     : Initialize Poetry and install all dependencies"
	@echo "make check         : Run tests with coverage (85% gate)"
	@echo "make lint          : Run quality checks (Ruff, Black, Mypy)"
	@echo "make format        : Auto-fix formatting and imports"
	@echo "make security      : Run security audits (Bandit, Checkov, Pip-audit)"
	@echo "make test          : Run tests"
	@echo "make coverage      : Generate coverage report"
	@echo "make clean         : Clean build artifacts"
	@echo "make build         : Build wheel and sdist"

install:
	$(PIP) install -e .
	@echo "✅ Installed in editable mode"

bootstrap:
	@echo "Initializing environment..."
	rm -f poetry.lock
	$(POETRY) install --with dev
	@echo "✅ Environment ready"

check: format security
	@echo "Running tests with 85% coverage gate..."
	rm -f .coverage
	$(PYTEST) --cov=skills --cov-config=pyproject.toml --cov-report=term-missing --cov-report=html

test:
	@echo "Running tests..."
	$(PYTEST)

coverage:
	@echo "Generating coverage report..."
	$(PYTEST) --cov=skills --cov-report=html
	@echo "Coverage report: htmlcov/index.html"

lint:
	@echo "Linting..."
	$(RUFF) check skills tests
	$(BLACK) --check skills tests
	$(MYPY) skills

format:
	@echo "Auto-fixing formatting and imports..."
	$(RUFF) check skills tests --fix
	$(BLACK) skills tests

security:
	@echo "Running security checks..."
	$(BANDIT) -r skills -s B101,B404,B603,B607
	$(PIP) install checkov &>/dev/null && checkov -d skills --quiet || true
	$(PIP) install pip-audit &>/dev/null && pip-audit || true

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .coverage htmlcov .mypy_cache .ruff_cache
	find . -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	find . -name "*_manifest_*.txt" -delete
	@echo "✅ Cleaned"

build:
	@echo "Building distribution..."
	$(POETRY) build
	@echo "✅ Built artifacts in dist/"

publish: build
	@echo "Publishing to PyPI..."
	$(POETRY) publish
	@echo "✅ Published"

.DEFAULT_GOAL := help
