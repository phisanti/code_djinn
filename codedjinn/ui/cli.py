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
    typer.echo(f"Response: {content}")


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

    This is intentionally minimal to validate Agno wiring.
    """
    parsed = run_and_parse(run)
    _print_result(parsed)


def run() -> None:
    """Entry point for console script mapping."""
    app()


if __name__ == "__main__":
    run()
