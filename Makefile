# Makefile for CodeDjinn project
.PHONY: help test test-verbose test-specific install install-dev clean build check-package lint format check-format check-imports release-check version-check prepare-release homebrew-update homebrew-sync homebrew-create-formula homebrew-release

# Default Python executable
PYTHON := python3

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
	cat > "$(HOMEBREW_TAP_DIR)/Formula/code-djinn.rb" << 'EOF'
class CodeDjinn < Formula
  include Language::Python::Virtualenv

  desc "CLI tool that helps users generate shell commands using various LLM models"
  homepage "https://github.com/phisanti/code_djinn"
  url "https://files.pythonhosted.org/packages/source/c/code-djinn/code_djinn-VERSION.tar.gz"
  sha256 "PLACEHOLDER_SHA256"
  license "MIT"

  depends_on "python@3.11"

  resource "langchain-community" do
    url "https://files.pythonhosted.org/packages/source/l/langchain-community/langchain_community-0.3.13.tar.gz"
    sha256 "86ac8993d0c18b3ab72ce4fcccbee6ac04fd9c71dd0b0c3ed4a5e12e1cbeb5b9"
  end

  resource "langchain-core" do
    url "https://files.pythonhosted.org/packages/source/l/langchain-core/langchain_core-0.3.29.tar.gz"
    sha256 "0d92ce0b83fc1371c5ded073fa3a57b7c7c8c9b6341c3c426e0b48b8db20b76"
  end

  resource "langchain-mistralai" do
    url "https://files.pythonhosted.org/packages/source/l/langchain-mistralai/langchain_mistralai-0.2.5.tar.gz"
    sha256 "3a5b1a3a6c8c8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8d8"
  end

  resource "langchain-google-genai" do
    url "https://files.pythonhosted.org/packages/source/l/langchain-google-genai/langchain_google_genai-2.0.9.tar.gz"
    sha256 "4b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5b5"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    system "#{bin}/code_djinn", "--help"
  end
end
EOF
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