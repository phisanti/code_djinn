import typer

from codedjinn.core.agent import run_and_parse
from codedjinn.prompts.system_prompt import get_system_prompt

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Code Djinn CLI (Agno-based).",
)


def _print_result(result: dict[str, str]) -> None:
    """Minimal, structured output for now."""
    content = result.get("content", "")
    typer.echo(f"Response:\n{content}")


@app.command()
def main(
    run: str = typer.Option(
        ...,
        "--run",
        "-r",
        help="Prompt to send to the Code Djinn agent.",
    ),
    steps: int = typer.Option(
        3,
        "--steps",
        help="Maximum step budget (approx: tool calls + final answer).",
        min=1,
    ),
) -> None:
    """
    Generate a command/answer via the configured agent.

    This version enables shell tools so the agent can execute commands.
    """
    instructions = get_system_prompt()
    parsed = run_and_parse(
        run,
        include_tools=True,
        instructions_override=instructions,
        max_steps=steps,
    )
    _print_result(parsed)


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
