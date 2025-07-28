# GitHub Actions Workflows

This directory contains GitHub Actions workflows for automated testing, building, and publishing of the CodeDjinn package.

## Workflows

### 1. `publish-to-pypi.yml` - Automatic PyPI Publishing

**Triggers:**
- When a release is published on GitHub
- Manual trigger via workflow_dispatch

**What it does:**
1. **Tests** the package on Python 3.10, 3.11, and 3.12
2. **Builds** source and wheel distributions
3. **Verifies** the distributions with twine
4. **Publishes** to PyPI using trusted publishing (no API keys needed)

**Usage:**
```bash
# Create a new release
git tag v0.2.2
git push origin v0.2.2

# Create release on GitHub UI or via gh CLI
gh release create v0.2.2 --title "Release v0.2.2" --notes "Brief description of changes"
```

### 2. `test.yml` - Continuous Integration Testing

**Triggers:**
- Push to master/main branch
- Pull requests to master/main branch

**What it does:**
1. **Tests** on multiple OS (Ubuntu, macOS, Windows) and Python versions
2. **Lints** code with flake8, black, and isort
3. **Validates** package imports and CLI functionality

### 3. `build-test.yml` - Package Build Validation

**Triggers:**
- Manual trigger via workflow_dispatch
- Push to master/main when package files change

**What it does:**
1. **Builds** the package (wheel and source distribution)
2. **Verifies** package integrity with twine
3. **Tests** installation and basic functionality

## Setup Requirements

### 1. PyPI Trusted Publishing Setup

To enable automatic PyPI publishing, you need to configure trusted publishing:

1. **Go to PyPI** → Account Settings → Publishing
2. **Add a new publisher** with these settings:
   - **PyPI Project Name**: `codedjinn`
   - **Owner**: `your-github-username`
   - **Repository name**: `code_djinn`
   - **Workflow name**: `publish-to-pypi.yml`
   - **Environment name**: `pypi`

3. **Create the PyPI environment** in your GitHub repository:
   - Go to Settings → Environments
   - Create new environment named `pypi`
   - Add deployment protection rules if desired

### 2. Version Management

Update version numbers in these files before creating a release:
- `setup.py` - Line 6: `version="0.2.2"`
- `pyproject.toml` - Line 7: `version = "0.2.2"`

### 3. Release Process

1. **Update version numbers** in setup.py and pyproject.toml
2. **Test locally** to ensure everything works
3. **Commit and push** changes
4. **Create and push a tag**:
   ```bash
   git tag v0.2.2
   git push origin v0.2.2
   ```
5. **Create a GitHub release** (triggers the publish workflow)
6. **Monitor the workflow** in the Actions tab

## Workflow Status Badges

Add these badges to your README.md:

```markdown
![Test](https://github.com/your-username/code_djinn/workflows/Test/badge.svg)
![PyPI Publish](https://github.com/your-username/code_djinn/workflows/Upload%20Python%20Package/badge.svg)
```

## Troubleshooting

### Common Issues

1. **Tests fail**: Check the test logs in the Actions tab
2. **Build fails**: Verify setup.py and pyproject.toml are valid
3. **PyPI publish fails**: Ensure trusted publishing is configured correctly
4. **Import errors**: Check that all dependencies are listed in setup.py

### Manual Testing

Test the workflows locally before pushing:

```bash
# Test package build
python -m build
python -m twine check dist/*

# Test installation
pip install dist/*.whl
python -c "import codedjinn; print('Success!')"

# Run tests
python -m pytest tests/ -v
```

### Security Notes

- **No API keys** are stored in the repository (using trusted publishing)
- **Workflows only run** on specific triggers (releases, PRs)
- **Environment protection** can be added for additional security