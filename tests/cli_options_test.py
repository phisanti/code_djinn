from typer.testing import CliRunner

from codedjinn.ui.cli import app


def test_ask_accepts_step_alias_in_help() -> None:
    """Users often type singular --step; keep it as a documented alias."""
    result = CliRunner().invoke(app, ["ask", "--help"])

    assert result.exit_code == 0
    assert "--steps" in result.output
    assert "--step" in result.output


def test_run_accepts_step_alias_in_help() -> None:
    """Run mode should expose the same option spelling as ask mode."""
    result = CliRunner().invoke(app, ["run", "--help"])

    assert result.exit_code == 0
    assert "--steps" in result.output
    assert "--step" in result.output
