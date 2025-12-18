"""Main CLI entry point for djinn_mistral branch."""

import sys
from pathlib import Path
from typing import Optional
import typer

from codedjinn.core.configs import load_raw_config, get_model_config
from codedjinn.core.policy import check_and_confirm
from codedjinn.core.session import Session  # NEW: Session management
from codedjinn.providers.mistral import MistralAgent
from codedjinn.tools.exec_shell import execute_command
from codedjinn.tools.output_trimmer import trim_output  # NEW: Output trimming

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Code Djinn CLI (Native Mistral implementation).",
)


@app.command()
def main(
    run: Optional[str] = typer.Option(
        None,
        "--run",
        "-r",
        help="Prompt to send to the Code Djinn agent.",
    ),
    ask: Optional[str] = typer.Option(
        None,
        "--ask",
        help="Ask a question about the previous command output (no execution).",
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
    no_confirm: bool = typer.Option(
        False,
        "--no-confirm",
        help="Skip safety confirmation prompts (use with caution).",
    ),
    no_context: bool = typer.Option(  # NEW flag
        False,
        "--no-context",
        help="Ignore previous command context (start fresh session).",
    ),
) -> None:
    """
    Generate and execute a command via the configured Mistral agent.

    This version uses native Mistral tool calling for maximum speed,
    bypassing the Agno framework entirely.

    NOW WITH CONTEXT: Remembers the previous command and its output,
    enabling natural follow-up commands.
    """
    if run is not None and ask is not None:
        typer.echo("Error: Use only one of --run or --ask.", err=True)
        raise typer.Exit(2)

    if run is None and ask is None:
        typer.echo("Error: You must provide either --run or --ask.", err=True)
        raise typer.Exit(2)

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

    # Step 5B: Load session and get previous context (NEW)
    session = Session(session_name="default")

    if no_context:
        # User wants fresh start - clear session
        session.clear()
        previous_context = None
    else:
        # Load previous context if available
        previous_context = session.get_context_for_prompt()

        if previous_context and verbose:
            # Show user that we have context
            typer.echo(f"[Using context from previous command: {previous_context['command']}]")

    if ask is not None:
        try:
            response = agent.analyze(
                ask,
                context,
                previous_context=previous_context,
            )
        except Exception as e:
            typer.echo(f"Error generating answer: {e}", err=True)
            raise typer.Exit(1)

        typer.echo(response)
        return

    # Step 6: Generate command WITH CONTEXT (MODIFIED)
    query = run
    try:
        command = agent.generate_command(
            query,
            context,
            previous_context=previous_context  # NEW: pass context
        )
    except Exception as e:
        typer.echo(f"Error generating command: {e}", err=True)
        raise typer.Exit(1)

    # Step 7: Show command if verbose mode
    if verbose:
        typer.echo(f"→ {command}")
        typer.echo()  # Blank line for readability

    # Step 8: Safety check - confirm dangerous commands
    if not no_confirm:
        if not check_and_confirm(command):
            typer.echo("Command execution cancelled by user.", err=True)
            raise typer.Exit(1)

    # Step 9: Execute command AND CAPTURE OUTPUT (MODIFIED)
    # Note: Full output is streamed to user's terminal in real-time
    exit_code, output = execute_command(command, cwd=context['cwd'])

    # Step 10: Save to session for next command (NEW)
    if not no_context:
        # Trim output for model context (user sees full output above)
        # This is "input trimming" - trimming what goes INTO the session/model context
        trimmed_for_context = trim_output(output, max_lines=30, max_chars=2000)
        session.save(command, trimmed_for_context, exit_code)

    # Step 11: Exit with command's exit code
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
