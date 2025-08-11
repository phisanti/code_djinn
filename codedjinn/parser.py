#!/usr/bin/env python3
"""
Argument parser module for CodeDjinn CLI.
Handles all command-line argument parsing functionality.
"""

import argparse
from typing import List, Any, Optional


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser with minimal imports."""
    parser = argparse.ArgumentParser(
        prog="code_djinn", description="An AI CLI assistant"
    )
    parser.add_argument(
        "-i", "--init", action="store_true", help="Initialize the configuration"
    )
    parser.add_argument(
        "-t",
        "--test",
        metavar="WISH",
        type=str,
        nargs="?",
        const="",
        help="Test the prompt for the given wish",
    )
    parser.add_argument(
        "-e",
        "--explain",
        action="store_true",
        default=False,
        help="Also provide an explanation for the command",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Verbose output from AI",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available models for all providers",
    )
    parser.add_argument(
        "-r",
        "--run",
        metavar="WISH",
        type=str,
        nargs="?",
        const="",
        help="Generate and run a shell command (with confirmation by default)",
    )
    parser.add_argument(
        "--no-confirm",
        action="store_true",
        default=False,
        help="Skip confirmation for safe commands when using --run",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear LLM client cache for troubleshooting",
    )
    parser.add_argument(
        "--chat",
        metavar="SESSION_ID",
        type=str,
        nargs="?",
        const="",
        help="Start interactive chat mode (optionally resume session)",
    )
    return parser


def get_user_selection(items: List[Any], prompt: str) -> Optional[Any]:
    """Helper function to display numbered items and get user selection.

    Args:
        items: List of items to display
        prompt: Prompt message for user input

    Returns:
        The selected item from the list, or None if selection fails
    """
    from .utils import print_text
    
    items_list = " | ".join([f"{i + 1}. {item}" for i, item in enumerate(items)])
    print_text(items_list, "blue")

    selection = None
    while selection is None:
        try:
            choice = input(f"\n{prompt}")
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                selection = items[idx]
            else:
                print_text(f"Invalid selection. Please try again.", "red")
        except ValueError:
            print_text("Please enter a number.", "red")
    return selection