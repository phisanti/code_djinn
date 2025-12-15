import typer

from codedjinn.core.agent import run_and_parse

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Code Djinn CLI (Agno-based).",
)


def _print_result(result: dict[str, str]) -> None:
    """Minimal, structured output for now."""
    content = result.get("content", "")
    model = result.get("model", "")
    typer.echo(f"Model: {model}")
    typer.echo(f"Response:\n{content}")


@app.command()
def main(
    run: str = typer.Option(
        ...,
        "--run",
        "-r",
        help="Prompt to send to the Code Djinn agent.",
    ),
) -> None:
    """
    Generate a command/answer via the configured agent.

    This version enables shell tools so the agent can execute commands.
    """
    instructions = (
        "You are Code Djinn. Use the provided shell tools to run the user's "
        "request in the current working directory. Return only the stdout."
    )
    parsed = run_and_parse(
        run,
        include_tools=True,
        instructions_override=instructions,
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
