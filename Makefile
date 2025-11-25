.PHONY: help install install-dev install-build lint format typecheck test test-cov test-all test-perf clean clean-all build build-wheels publish bump-patch bump-minor bump-major run-basic run-advanced annotate-cython ci-local

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
UV := uv
VENV_PYTHON := .venv/bin/python
PACKAGE_NAME := fastapi-advanced
SRC_DIR := src/fastapi_advanced
TESTS_DIR := tests
EXAMPLES_DIR := examples

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install package dependencies using uv
	$(UV) pip install -e .

install-dev: ## Install package with development dependencies using uv
	$(UV) pip install -e ".[dev,examples]"

install-build: ## Install build dependencies (Cython, setuptools, wheel)
	@echo "Installing build dependencies..."
	$(UV) pip install -e ".[build]"
	@echo "✓ Build dependencies installed!"

lint: ## Run ruff linter
	@echo "Running ruff linter..."
	$(UV) run ruff check $(SRC_DIR) $(TESTS_DIR) $(EXAMPLES_DIR)

lint-fix: ## Run ruff linter with auto-fix
	@echo "Running ruff linter with auto-fix..."
	$(UV) run ruff check --fix $(SRC_DIR) $(TESTS_DIR) $(EXAMPLES_DIR)

format: ## Format code with ruff
	@echo "Formatting code with ruff..."
	$(UV) run ruff format $(SRC_DIR) $(TESTS_DIR) $(EXAMPLES_DIR)

format-check: ## Check code formatting without making changes
	@echo "Checking code formatting..."
	$(UV) run ruff format --check $(SRC_DIR) $(TESTS_DIR) $(EXAMPLES_DIR)

typecheck: ## Run mypy type checker
	@echo "Running mypy type checker..."
	$(UV) run mypy $(SRC_DIR)

check: lint format-check typecheck ## Run all checks (lint, format, typecheck)
	@echo "All checks passed!"

test: ## Run tests with pytest
	@echo "Running tests..."
	$(UV) run pytest $(TESTS_DIR) -v

test-cov: ## Run tests with coverage report
	@echo "Running tests with coverage..."
	$(UV) run pytest $(TESTS_DIR) --cov=$(SRC_DIR) --cov-report=term-missing --cov-report=html

test-watch: ## Run tests in watch mode
	$(UV) run pytest-watch $(TESTS_DIR)

test-all: ## Run tests across all supported Python versions (requires pyenv)
	@echo "Testing on Python 3.10..."
	@pyenv local 3.10 && $(PYTHON) -m pytest $(TESTS_DIR) -v || echo "Python 3.10 not available"
	@echo "Testing on Python 3.11..."
	@pyenv local 3.11 && $(PYTHON) -m pytest $(TESTS_DIR) -v || echo "Python 3.11 not available"
	@echo "Testing on Python 3.12..."
	@pyenv local 3.12 && $(PYTHON) -m pytest $(TESTS_DIR) -v || echo "Python 3.12 not available"
	@echo "Testing on Python 3.13..."
	@pyenv local 3.13 && $(PYTHON) -m pytest $(TESTS_DIR) -v || echo "Python 3.13 not available"

test-perf: ## Run performance regression tests
	@echo "Running performance regression tests..."
	$(UV) run pytest $(TESTS_DIR) -v -m benchmark

clean: ## Clean up build artifacts and cache
	@echo "Cleaning up..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

clean-all: clean clean-cython ## Clean all build artifacts including Cython
	@echo "✓ All artifacts cleaned!"

build: clean ## Build package distribution (source + wheel)
	@echo "Building package..."
	$(UV) run python -m build

build-wheels: install-build ## Build binary wheels for distribution
	@echo "Building binary wheels..."
	$(UV) run python -m build --wheel
	@echo "✓ Wheels built in dist/"
	@ls -lh dist/*.whl

publish-test: build ## Publish package to TestPyPI
	@echo "Publishing to TestPyPI..."
	$(UV) publish --index testpypi

publish: build ## Publish package to PyPI
	@echo "Publishing to PyPI..."
	$(UV) publish

bump-patch: ## Bump patch version (0.1.0 -> 0.1.1)
	@echo "Bumping patch version..."
	$(UV) run bump2version patch

bump-minor: ## Bump minor version (0.1.0 -> 0.2.0)
	@echo "Bumping minor version..."
	$(UV) run bump2version minor

bump-major: ## Bump major version (0.1.0 -> 1.0.0)
	@echo "Bumping major version..."
	$(UV) run bump2version major

run-basic: ## Run basic example application
	@echo "Running basic example on http://localhost:8000"
	$(UV) run uvicorn examples.basic:app --reload

run-advanced: ## Run advanced example application
	@echo "Running advanced example on http://localhost:8000"
	$(UV) run uvicorn examples.advanced:app --reload

run-migration: ## Run migration example application
	@echo "Running migration example on http://localhost:8000"
	$(UV) run uvicorn examples.migration_from_pydantic:msgspec_app --reload

docs-serve: ## Serve documentation locally
	@echo "Serving documentation on http://localhost:8080"
	$(PYTHON) -m http.server 8080 --directory docs

pre-commit: check test ## Run all pre-commit checks
	@echo "Pre-commit checks passed!"

ci: install-dev check test-cov ## Run full CI pipeline
	@echo "CI pipeline completed!"

ci-local: install-dev compile-cython check test-cov test-perf ## Run full CI pipeline locally including Cython
	@echo "✓ Local CI pipeline completed!"

# Cython Performance Extensions
install-cython: ## Install Cython and build dependencies (deprecated, use install-build)
	@echo "Installing Cython and build dependencies..."
	$(VENV_PYTHON) -m pip install cython setuptools wheel
	@echo "✓ Cython installed!"

compile-cython: install-build ## Compile Cython extensions for performance
	@echo "Compiling Cython extensions..."
	$(VENV_PYTHON) setup.py build_ext --inplace
	@echo "✓ Cython extensions compiled successfully!"
	@echo ""
	@echo "Verify Cython is loaded:"
	@$(VENV_PYTHON) -c "from fastapi_advanced import _CYTHON_AVAILABLE; print('✓ Cython available!' if _CYTHON_AVAILABLE else '✗ Using Python fallback')"

clean-cython: ## Clean Cython build artifacts
	@echo "Cleaning Cython artifacts..."
	rm -f $(SRC_DIR)/_speedups.c
	rm -f $(SRC_DIR)/_speedups.*.so
	rm -f $(SRC_DIR)/_speedups.html
	rm -rf build/
	@echo "✓ Cython artifacts cleaned!"

annotate-cython: install-build ## Generate Cython optimization annotations (HTML)
	@echo "Generating Cython annotations..."
	$(VENV_PYTHON) -m cython -a src/fastapi_advanced/_speedups.pyx -o $(SRC_DIR)/_speedups_annotated.html
	@echo "✓ Annotation generated: $(SRC_DIR)/_speedups_annotated.html"
	@echo "Open this file in a browser to see optimization opportunities (yellow = Python overhead)"

check-cython: ## Check if Cython extensions are available
	@$(VENV_PYTHON) -c "from fastapi_advanced import _CYTHON_AVAILABLE; import sys; print('✓ Cython extensions available' if _CYTHON_AVAILABLE else '✗ Using pure Python fallback'); sys.exit(0 if _CYTHON_AVAILABLE else 1)"

benchmark: ## Run performance benchmarks
	@echo "Running comprehensive performance analysis..."
	$(VENV_PYTHON) benchmarks/profiling/comprehensive_performance_analysis.py

benchmark-cython: compile-cython ## Run Cython vs Python comparison benchmark
	@echo "Running Cython vs Python benchmark..."
	$(VENV_PYTHON) benchmarks/profiling/benchmark_cython_vs_python.py

profile-all: ## Run all profiling scripts
	@echo "Running serialization profiling..."
	$(VENV_PYTHON) benchmarks/profiling/profile_serialization.py
	@echo ""
	@echo "Running comprehensive analysis..."
	$(VENV_PYTHON) benchmarks/profiling/comprehensive_performance_analysis.py
