#!/usr/bin/env python3
"""
Main entry point for the Typer-based Code Djinn CLI.

This delegates to the UI layer in codedjinn.ui.cli to keep the
console script mapping stable while we migrate to Agno.
"""

from codedjinn.ui.cli import run as code_djinn


if __name__ == "__main__":
    code_djinn()
