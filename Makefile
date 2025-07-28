# Makefile for CodeDjinn project
.PHONY: help test test-verbose test-specific install install-dev clean build check-package lint format check-format check-imports release-check version-check prepare-release

# Default Python executable
PYTHON := python3

# Help target
help: ## Show this help message
	@echo "CodeDjinn Development Commands"
	@echo "=============================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Testing targets
test: ## Run all unit tests
	@echo "🧪 Running all unit tests..."
	@echo "=" | head -c 60; echo ""
	$(PYTHON) -m pytest tests/ -v --tb=short

test-verbose: ## Run tests with extra verbose output
	@echo "🧪 Running tests with verbose output..."
	@echo "=" | head -c 60; echo ""
	$(PYTHON) -m pytest tests/ -vv --tb=long

test-specific: ## Run specific test module (usage: make test-specific MODULE=config)
	@echo "🧪 Running tests for module: test_$(MODULE).py"
	@echo "=" | head -c 60; echo ""
	$(PYTHON) -m pytest tests/test_$(MODULE).py -v --tb=short

# Installation targets
install: ## Install package in development mode
	@echo "📦 Installing CodeDjinn in development mode..."
	$(PYTHON) -m pip install -e .

install-dev: ## Install package with development dependencies
	@echo "📦 Installing CodeDjinn with development dependencies..."
	$(PYTHON) -m pip install -e .
	$(PYTHON) -m pip install pytest flake8 black isort build twine

# Cleaning targets
clean: ## Clean build artifacts and cache files
	@echo "🧹 Cleaning build artifacts..."
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# Code quality targets
lint: ## Run flake8 linting
	@echo "🔍 Running flake8 linting..."
	$(PYTHON) -m flake8 codedjinn --count --select=E9,F63,F7,F82 --show-source --statistics
	$(PYTHON) -m flake8 codedjinn --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

format: ## Format code with black
	@echo "🎨 Formatting code with black..."
	$(PYTHON) -m black codedjinn/

check-format: ## Check code formatting with black
	@echo "🔍 Checking code formatting..."
	$(PYTHON) -m black --check --diff codedjinn/

check-imports: ## Check import sorting with isort
	@echo "🔍 Checking import sorting..."
	$(PYTHON) -m isort --check-only --diff codedjinn/

# Build and package targets
build: clean ## Build source and wheel distributions
	@echo "🏗️ Building package..."
	$(PYTHON) -m build

check-package: build ## Check package integrity with twine
	@echo "🔍 Checking package integrity..."
	$(PYTHON) -m twine check dist/*

# Version management
version-check: ## Check version consistency across files
	@echo "🔍 Checking version consistency..."
	@echo "=" | head -c 50; echo ""
	@setup_version=$$(grep 'version=' setup.py | sed 's/.*version="\([^"]*\)".*/\1/'); \
	pyproject_version=$$(grep 'version =' pyproject.toml | sed 's/.*version = "\([^"]*\)".*/\1/'); \
	if [ "$$setup_version" = "$$pyproject_version" ]; then \
		echo "✅ Version consistency - Both files have version $$setup_version"; \
	else \
		echo "❌ Version mismatch: setup.py=$$setup_version, pyproject.toml=$$pyproject_version"; \
		exit 1; \
	fi

# Import test
test-import: ## Test that package can be imported
	@echo "🔍 Testing package import..."
	@$(PYTHON) -c "import codedjinn; print('✅ Package imports successfully')"

# Release preparation
release-check: version-check test test-import build check-package ## Run all release checks
	@echo ""
	@echo "🎉 All release checks passed!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Commit any final changes"
	@echo "2. Create and push a git tag: git tag vX.Y.Z && git push origin vX.Y.Z"
	@echo "3. Create a GitHub release to trigger automatic PyPI publishing"
	@echo "4. Monitor the GitHub Actions workflow"

prepare-release: release-check ## Alias for release-check (backward compatibility)

# Development workflow targets
dev-setup: install-dev ## Complete development environment setup
	@echo "🚀 Development environment ready!"
	@echo "Available commands:"
	@make help

# Quick development cycle
dev-test: lint test ## Quick development test cycle (lint + test)

# CI/CD simulation
ci-test: install test lint check-format check-imports test-import ## Simulate CI/CD pipeline locally