from typer.testing import CliRunner

from codedjinn.ui.cli import app


def test_ask_accepts_step_alias_in_help() -> None:
    result = CliRunner().invoke(app, ["ask", "--help"])

    assert result.exit_code == 0
    assert "--steps" in result.output
    assert "--step" in result.output


def test_run_accepts_step_alias_in_help() -> None:
    result = CliRunner().invoke(app, ["run", "--help"])

    assert result.exit_code == 0
    assert "--steps" in result.output
    assert "--step" in result.output
