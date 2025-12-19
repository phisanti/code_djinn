"""Main CLI entry point - clean subcommand architecture."""

import sys
from pathlib import Path
from typing import Optional, Tuple
import typer

from codedjinn.core.configs import load_raw_config, get_model_config
from codedjinn.core.policy import check_and_confirm
from codedjinn.core.session import Session
from codedjinn.providers.mistral import MistralAgent
from codedjinn.tools.exec_shell import execute_command
from codedjinn.tools.output_trimmer import trim_output

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Code Djinn - Your AI shell command assistant.",
)


# ============================================================================
# Shared Setup - Performance critical: called on every invocation
# ============================================================================

def _setup_agent_and_context() -> Tuple:
    """
    Load config and create agent. Exits on error.

    Returns: (agent, context_dict)

    Performance: Config loading is cached, agent creation is fast.
    Future agents: This is the single source of truth for agent setup.
    """
    try:
        raw_config = load_raw_config()
        model_config = get_model_config(raw_config)
    except Exception as e:
        typer.echo(f"Error loading configuration: {e}", err=True)
        typer.echo("Run 'code-djinn settings init' to set up configuration", err=True)
        raise typer.Exit(1)

    # Warn if not using mistralai (but continue - user may be testing)
    if model_config.provider != 'mistralai':
        typer.echo(
            f"WARNING: Currently only supports 'mistralai' provider (got: {model_config.provider})",
            err=True
        )

    try:
        agent = MistralAgent(api_key=model_config.api_key, model=model_config.model)
    except Exception as e:
        typer.echo(f"Error initializing agent: {e}", err=True)
        raise typer.Exit(1)

    # Build execution context - minimal dict for performance
    context = {
        'cwd': Path.cwd(),
        'os_name': raw_config.get('os', 'Linux'),
        'shell': raw_config.get('shell', 'bash')
    }

    return agent, context


def _get_session_context(no_context: bool, verbose: bool) -> Tuple:
    """
    Load session and previous context.

    Returns: (session, previous_context_dict_or_none)

    Performance: Session loading is I/O bound, unavoidable.
    Future agents: --no-context flag clears session, otherwise loads previous command.
    """
    session = Session(session_name="default")

    if no_context:
        session.clear()
        return session, None

    previous_context = session.get_context_for_prompt()
    if previous_context and verbose:
        typer.echo(f"[Using context from: {previous_context['command']}]")

    return session, previous_context


# ============================================================================
# Commands - Each command is linear: setup → execute → handle result
# ============================================================================

@app.command()
def ask(
    query: str = typer.Argument(..., help="Question about previous command output"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
    no_context: bool = typer.Option(False, "--no-context", help="Ignore previous context"),
) -> None:
    """
    Ask a question about the previous command output (no execution).

    Example: code-djinn ask "what files were modified?"
    """
    agent, context = _setup_agent_and_context()
    _, previous_context = _get_session_context(no_context, verbose)

    try:
        response = agent.analyze(query, context, previous_context=previous_context)
        typer.echo(response)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def run(
    query: str = typer.Argument(..., help="Prompt to generate and execute command"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
    silent: bool = typer.Option(False, "--silent", help="Suppress echoing the generated command"),
    no_confirm: bool = typer.Option(False, "--no-confirm", help="Skip safety confirmation"),
    no_context: bool = typer.Option(False, "--no-context", help="Ignore previous context"),
    steps: int = typer.Option(0, "--steps", min=0, help="Tool call budget (currently only 0 supported)"),
) -> None:
    """
    Generate and execute a shell command.

    Example: code-djinn run "find all python files modified today"

    Performance: Single-shot LLM call, command execution streams output in real-time.
    """
    # Validate steps parameter (Phase 1: single-shot only)
    if steps != 0:
        typer.echo("WARNING: Only --steps 0 supported. Using single-shot mode.", err=True)

    agent, context = _setup_agent_and_context()
    session, previous_context = _get_session_context(no_context, verbose)

    # Generate command (performance critical: LLM call)
    try:
        command = agent.generate_command(query, context, previous_context=previous_context)
    except Exception as e:
        typer.echo(f"Error generating command: {e}", err=True)
        raise typer.Exit(1)

    # Echo command unless configured to stay silent
    if not silent:
        typer.echo(f"→ {command}\n")

    # Safety check - user confirmation for dangerous commands
    if not no_confirm and not check_and_confirm(command):
        typer.echo("Cancelled by user.", err=True)
        raise typer.Exit(1)

    # Execute and capture output (performance: streams to terminal in real-time)
    exit_code, output = execute_command(command, cwd=context['cwd'])

    # Save to session for next command (performance: trim output to avoid bloat)
    if not no_context:
        trimmed_output = trim_output(output, max_lines=30, max_chars=2000)
        session.save(command, trimmed_output, exit_code)

    # Exit with command's actual exit code (preserves shell semantics)
    raise typer.Exit(exit_code)


@app.command()
def settings(
    action: str = typer.Argument(..., help="Action: init, show, or edit"),
) -> None:
    """
    Manage Code Djinn configuration.

    Actions:
        init - Interactive configuration wizard
        show - Display current configuration
        edit - Open config file in $EDITOR

    Performance: Lazy import config_commands to avoid startup overhead.
    """
    from codedjinn.ui.config_commands import handle_config
    handle_config(action)


def run() -> None:
    """Entry point for console script mapping."""
    app()


if __name__ == "__main__":
    run()
