# Makefile for CodeDjinn project
.PHONY: help test test-verbose test-specific install install-dev clean build check-package lint format check-format check-imports release-check version-check prepare-release homebrew-update homebrew-sync homebrew-create-formula homebrew-release clean-install

# Default Python executable - prefer conda environment
CONDA_ENV_PYTHON := /Users/santiago/miniconda3/envs/codedjinn_dev/bin/python
PYTHON := $(shell if [ -x "$(CONDA_ENV_PYTHON)" ]; then echo "$(CONDA_ENV_PYTHON)"; else which python3 2>/dev/null || echo python3; fi)

# Homebrew tap directory
HOMEBREW_TAP_DIR := ../homebrew-code-djinn

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

# Clean install removes previous installation then reinstalls via uv
clean-install: ## Clean install via uv after removing old install
	@echo "🧹 Running clean before forced uv install..."
	$(MAKE) clean
	@echo "🧪 Uninstalling any existing code-djinn package..."
	@$(PYTHON) -m pip uninstall -y code-djinn >/dev/null 2>&1 || true
	@echo "📦 Forcing fresh install via uv..."
	uv pip install -e . --python $(CONDA_ENV_PYTHON) --force-reinstall

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

# Homebrew tap management
homebrew-sync: ## Sync current project files to homebrew tap
	@echo "🍺 Syncing project to Homebrew tap..."
	@if [ ! -d "$(HOMEBREW_TAP_DIR)" ]; then \
		echo "❌ Homebrew tap directory not found: $(HOMEBREW_TAP_DIR)"; \
		echo "Please create the homebrew tap first"; \
		exit 1; \
	fi
	@current_version=$$(grep 'version =' pyproject.toml | sed 's/.*version = "\([^"]*\)".*/\1/'); \
	echo "📦 Current version: $$current_version"; \
	cd $(HOMEBREW_TAP_DIR) && \
	if [ ! -f "Formula/code-djinn.rb" ]; then \
		echo "⚠️  Formula not found, creating template..."; \
		$(MAKE) -C ../code_djinn homebrew-create-formula; \
	fi; \
	echo "✅ Homebrew tap synced"

homebrew-create-formula: ## Create initial Homebrew formula
	@echo "🍺 Creating Homebrew formula..."
	@current_version=$$(grep 'version =' pyproject.toml | sed 's/.*version = "\([^"]*\)".*/\1/'); \
	if [ ! -d "$(HOMEBREW_TAP_DIR)/Formula" ]; then \
		mkdir -p "$(HOMEBREW_TAP_DIR)/Formula"; \
	fi; \
	echo 'class CodeDjinn < Formula' > "$(HOMEBREW_TAP_DIR)/Formula/code-djinn.rb"; \
	echo '  include Language::Python::Virtualenv' >> "$(HOMEBREW_TAP_DIR)/Formula/code-djinn.rb"; \
	echo '' >> "$(HOMEBREW_TAP_DIR)/Formula/code-djinn.rb"; \
	echo '  desc "CLI tool that helps users generate shell commands using various LLM models"' >> "$(HOMEBREW_TAP_DIR)/Formula/code-djinn.rb"; \
	echo '  homepage "https://github.com/phisanti/code_djinn"' >> "$(HOMEBREW_TAP_DIR)/Formula/code-djinn.rb"; \
	echo '  url "https://files.pythonhosted.org/packages/source/c/code-djinn/code_djinn-VERSION.tar.gz"' >> "$(HOMEBREW_TAP_DIR)/Formula/code-djinn.rb"; \
	echo '  sha256 "PLACEHOLDER_SHA256"' >> "$(HOMEBREW_TAP_DIR)/Formula/code-djinn.rb"; \
	echo '  license "MIT"' >> "$(HOMEBREW_TAP_DIR)/Formula/code-djinn.rb"; \
	echo '' >> "$(HOMEBREW_TAP_DIR)/Formula/code-djinn.rb"; \
	echo '  depends_on "python@3.11"' >> "$(HOMEBREW_TAP_DIR)/Formula/code-djinn.rb"; \
	echo '' >> "$(HOMEBREW_TAP_DIR)/Formula/code-djinn.rb"; \
	echo '  def install' >> "$(HOMEBREW_TAP_DIR)/Formula/code-djinn.rb"; \
	echo '    virtualenv_install_with_resources' >> "$(HOMEBREW_TAP_DIR)/Formula/code-djinn.rb"; \
	echo '  end' >> "$(HOMEBREW_TAP_DIR)/Formula/code-djinn.rb"; \
	echo '' >> "$(HOMEBREW_TAP_DIR)/Formula/code-djinn.rb"; \
	echo '  test do' >> "$(HOMEBREW_TAP_DIR)/Formula/code-djinn.rb"; \
	echo '    system "#{bin}/code_djinn", "--help"' >> "$(HOMEBREW_TAP_DIR)/Formula/code-djinn.rb"; \
	echo '  end' >> "$(HOMEBREW_TAP_DIR)/Formula/code-djinn.rb"; \
	echo 'end' >> "$(HOMEBREW_TAP_DIR)/Formula/code-djinn.rb"
	@echo "✅ Homebrew formula created"

homebrew-update: homebrew-sync ## Update Homebrew formula with current version
	@echo "🍺 Updating Homebrew formula..."
	@current_version=$$(grep 'version =' pyproject.toml | sed 's/.*version = "\([^"]*\)".*/\1/'); \
	echo "📦 Updating to version: $$current_version"; \
	cd $(HOMEBREW_TAP_DIR) && \
	if [ ! -f "Formula/code-djinn.rb" ]; then \
		echo "❌ Formula not found, run 'make homebrew-create-formula' first"; \
		exit 1; \
	fi; \
	echo "🔄 Fetching SHA256 for version $$current_version..."; \
	tarball_url="https://files.pythonhosted.org/packages/source/c/code-djinn/code_djinn-$$current_version.tar.gz"; \
	sha256_hash=$$(curl -sL "$$tarball_url" | shasum -a 256 | cut -d' ' -f1) || { \
		echo "⚠️  Could not fetch tarball, using placeholder SHA256"; \
		sha256_hash="PLACEHOLDER_SHA256"; \
	}; \
	sed -i '' "s/code_djinn-VERSION/code_djinn-$$current_version/g" "Formula/code-djinn.rb"; \
	sed -i '' "s/PLACEHOLDER_SHA256/$$sha256_hash/g" "Formula/code-djinn.rb"; \
	echo "✅ Formula updated with version $$current_version and SHA256: $$sha256_hash"; \
	echo "📝 Committing changes..."; \
	git add .; \
	git commit -m "Update code-djinn to version $$current_version" || echo "ℹ️  No changes to commit"; \
	echo "✅ Homebrew formula updated"

homebrew-release: release-check homebrew-update ## Complete release workflow including Homebrew update
	@echo "🎉 Complete release workflow finished!"
	@echo ""
	@current_version=$$(grep 'version =' pyproject.toml | sed 's/.*version = "\([^"]*\)".*/\1/'); \
	echo "Next steps:"; \
	echo "1. Push main project: git tag v$$current_version && git push origin v$$current_version"; \
	echo "2. Create GitHub release to trigger PyPI publishing"; \
	echo "3. Push Homebrew tap: cd $(HOMEBREW_TAP_DIR) && git push origin main"; \
	echo "4. Test installation: brew tap phisanti/code-djinn && brew install code-djinn"
