"""
Context Management Commands

CLI handlers for file context management.
This module is lazy-loaded only when context commands are used.
"""

import time
from typing import List, Optional

from rich.console import Console
from rich.table import Table

from codedjinn.context.sources.files import (
    get_file_context_manager,
    parse_duration,
    FileContextManager,
)

console = Console()


def handle_context(action: str, files: Optional[List[str]] = None, duration: str = "10m") -> None:
    """
    Route to appropriate context action.

    Args:
        action: One of 'add', 'list', 'drop', 'clear'
        files: File paths for add/drop actions
        duration: Duration string for add action (e.g., "10m", "1h")
    """
    if action == "add":
        if not files:
            console.print("[red]Error: Specify files to add[/red]")
            console.print("Usage: code-djinn context add <file1> [file2 ...]")
            raise SystemExit(1)
        context_add(files, duration)

    elif action == "list":
        context_list()

    elif action == "drop":
        if not files:
            console.print("[red]Error: Specify files to drop[/red]")
            console.print("Usage: code-djinn context drop <file1> [file2 ...]")
            raise SystemExit(1)
        context_drop(files)

    elif action == "clear":
        context_clear()

    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        console.print("Available actions: add, list, drop, clear")
        raise SystemExit(1)


def context_add(files: List[str], duration: str) -> None:
    """
    Add files to context.

    Args:
        files: List of file paths to add
        duration: Duration string (e.g., "10m", "1h", "1d")
    """
    manager = get_file_context_manager()
    duration_seconds = parse_duration(duration)

    result = manager.add_files(files, duration_seconds)

    # Report results
    if result['added']:
        console.print(f"[green]Added to context (expires in {_format_duration(duration_seconds)}):[/green]")
        for path in result['added']:
            # Show relative path if possible
            display = result['context'].files[-1].display_path if result['context'].files else path
            for f in result['context'].files:
                if f.path == path:
                    display = f.display_path
                    break
            console.print(f"  - {display}")

    if result['skipped']:
        console.print("[yellow]Skipped (non-text files):[/yellow]")
        for msg in result['skipped']:
            console.print(f"  - {msg}")

    if result['errors']:
        console.print("[red]Errors:[/red]")
        for msg in result['errors']:
            console.print(f"  - {msg}")

    # Summary
    ctx = result['context']
    if not ctx.is_empty():
        console.print(f"\n[dim]Context: {len(ctx.files)} file(s), "
                     f"{ctx.total_size // 1024}KB / {FileContextManager.MAX_TOTAL_SIZE // 1024}KB[/dim]")


def context_list() -> None:
    """List files currently in context."""
    manager = get_file_context_manager()
    ctx = manager.list_files()

    if ctx.is_empty():
        console.print("[dim]No files in context[/dim]")
        console.print("\n[dim]Add files with: code-djinn context add <file>[/dim]")
        return

    table = Table(title="Active Context Files", show_header=True)
    table.add_column("File", style="cyan")
    table.add_column("Size", style="green", justify="right")
    table.add_column("Expires In", style="yellow", justify="right")

    now = time.time()
    for f in ctx.files:
        remaining = int(f.expires_at - now)
        expires_str = _format_duration(remaining) if remaining > 0 else "expired"
        size_str = f"{f.size_bytes // 1024}KB" if f.size_bytes >= 1024 else f"{f.size_bytes}B"

        table.add_row(f.display_path, size_str, expires_str)

    console.print(table)
    console.print(f"\n[dim]Total: {len(ctx.files)} file(s), "
                 f"{ctx.total_size // 1024}KB / {FileContextManager.MAX_TOTAL_SIZE // 1024}KB, "
                 f"~{ctx.total_tokens:,} tokens[/dim]")


def context_drop(files: List[str]) -> None:
    """
    Remove files from context.

    Args:
        files: List of file paths to remove
    """
    manager = get_file_context_manager()
    removed = manager.drop_files(files)

    if removed:
        console.print("[green]Removed from context:[/green]")
        for path in removed:
            console.print(f"  - {path}")
    else:
        console.print("[yellow]No matching files found in context[/yellow]")

    # Show remaining
    ctx = manager.list_files()
    if not ctx.is_empty():
        console.print(f"\n[dim]Remaining: {len(ctx.files)} file(s)[/dim]")


def context_clear() -> None:
    """Clear all files from context."""
    manager = get_file_context_manager()
    count = manager.clear()

    if count > 0:
        console.print(f"[green]Cleared {count} file(s) from context[/green]")
    else:
        console.print("[dim]Context was already empty[/dim]")


def _format_duration(seconds: int) -> str:
    """Format seconds as human-readable duration."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if minutes > 0:
            return f"{hours}h {minutes}m"
        return f"{hours}h"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        if hours > 0:
            return f"{days}d {hours}h"
        return f"{days}d"
