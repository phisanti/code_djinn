"""Main CLI entry point for djinn_mistral branch."""

import sys
from pathlib import Path
import typer

from codedjinn.core.configs import load_raw_config, get_model_config
from codedjinn.providers.mistral import MistralAgent
from codedjinn.tools.exec_shell import execute_command

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Code Djinn CLI (Native Mistral implementation).",
)


@app.command()
def main(
    run: str = typer.Option(
        ...,
        "--run",
        "-r",
        help="Prompt to send to the Code Djinn agent.",
    ),
    steps: int = typer.Option(
        0,
        "--steps",
        help="Maximum tool call budget. Currently only 0 (single-shot) is supported.",
        min=0,
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show generated command before execution.",
    ),
) -> None:
    """
    Generate and execute a command via the configured Mistral agent.

    This version uses native Mistral tool calling for maximum speed,
    bypassing the Agno framework entirely.
    """
    # Step 1: Load configuration (reuse existing 99%)
    try:
        raw_config = load_raw_config()
        model_config = get_model_config(raw_config)
    except Exception as e:
        typer.echo(f"Error loading configuration: {e}", err=True)
        typer.echo("Run 'code-djinn config init' to set up configuration", err=True)
        raise typer.Exit(1)

    # Step 2: Validate provider (warn, don't fail)
    if model_config.provider != 'mistralai':
        typer.echo(
            f"WARNING: djinn_mistral branch currently only supports 'mistralai' provider",
            err=True
        )
        typer.echo(f"Current provider: {model_config.provider}", err=True)
        typer.echo(f"Attempting to use Mistral anyway...\n", err=True)

    # Step 3: Validate steps parameter
    if steps != 0:
        typer.echo(
            f"WARNING: Multi-step execution not implemented in Phase 1.",
            err=True
        )
        typer.echo(f"Only --steps 0 is supported. Using single-shot mode.\n", err=True)

    # Step 4: Create agent
    try:
        agent = MistralAgent(
            api_key=model_config.api_key,
            model=model_config.model
        )
    except Exception as e:
        typer.echo(f"Error initializing Mistral agent: {e}", err=True)
        raise typer.Exit(1)

    # Step 5: Build execution context
    os_name = raw_config.get('os', 'Linux')
    shell = raw_config.get('shell', 'bash')
    context = {
        'cwd': Path.cwd(),
        'os_name': os_name,
        'shell': shell
    }

    # Step 6: Generate command
    query = run
    try:
        command = agent.generate_command(query, context)
    except Exception as e:
        typer.echo(f"Error generating command: {e}", err=True)
        raise typer.Exit(1)

    # Step 7: Show command if verbose mode
    if verbose:
        typer.echo(f"→ {command}")
        typer.echo()  # Blank line for readability

    # Step 8: Execute command
    # NOTE: No safety checks in Phase 1 - add in future
    # TODO: Add confirmation prompt for dangerous commands
    # TODO: Add command validation/sandboxing
    exit_code = execute_command(command, cwd=context['cwd'])

    # Step 9: Exit with command's exit code
    raise typer.Exit(exit_code)


@app.command()
def config(
    action: str = typer.Argument(
        ...,
        help="Configuration action: init, show, or edit",
    ),
) -> None:
    """
    Manage Code Djinn configuration.

    Actions:
        init - Interactive configuration wizard
        show - Display current configuration
        edit - Open config file in $EDITOR
    """
    # Lazy load config commands to avoid runtime overhead
    from codedjinn.ui.config_commands import handle_config

    handle_config(action)


def run() -> None:
    """Entry point for console script mapping."""
    app()


if __name__ == "__main__":
    run()
