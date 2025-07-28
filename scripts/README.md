# Development Scripts

This directory contains Python scripts for development tasks. These scripts provide an alternative to the Makefile for environments where Make is not available or preferred.

## Scripts

### `run_tests.py`
Runs the project's unit tests using pytest.

```bash
# Run all tests
python scripts/run_tests.py

# Run specific test module
python scripts/run_tests.py config
```

### `prepare_release.py`
Comprehensive release preparation script that runs all necessary checks.

```bash
# Run all release checks
python scripts/prepare_release.py
```

This script performs:
- Version consistency check between setup.py and pyproject.toml
- Full test suite execution
- Package import verification
- Package build and integrity check
- Provides release preparation guidance

## Makefile Alternative

These scripts are provided as alternatives to the main Makefile commands:

| Makefile Command | Python Script Alternative |
|------------------|---------------------------|
| `make test` | `python scripts/run_tests.py` |
| `make release-check` | `python scripts/prepare_release.py` |

## Usage Recommendation

**Primary**: Use the Makefile commands (e.g., `make test`, `make release-check`)
**Fallback**: Use these Python scripts in environments without Make

The Makefile provides more features and is the recommended approach for development.