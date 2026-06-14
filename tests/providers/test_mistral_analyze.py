from pathlib import Path
from unittest.mock import Mock, patch

from codedjinn.providers.mistral import MistralAgent


def test_mistral_analyze_answers_directly_when_no_tool_needed() -> None:
    fake_response = Mock()
    fake_message = Mock()
    fake_message.content = "hello"
    fake_message.tool_calls = None  # No tool calls made
    fake_response.choices = [Mock(message=fake_message)]

    fake_client = Mock()
    fake_client.chat.complete = Mock(return_value=fake_response)

    with patch("codedjinn.providers.mistral.get_cached_client", return_value=fake_client):
        agent = MistralAgent(api_key="test", model="mistral-small-latest", use_cache=True)
        result = agent.analyze(
            "Summarize the previous output",
            context={"cwd": Path.cwd(), "os_name": "macOS", "shell": "zsh"},
            previous_context={"command": "ls", "output": "a\nb\nc\n", "exit_code": 0},
        )

    # analyze() now returns a dict with answer and tool_calls
    assert result["answer"] == "hello"
    assert result["tool_calls"] == []

    _, kwargs = fake_client.chat.complete.call_args
    assert "tools" in kwargs
    assert kwargs["tool_choice"] == "auto"
    assert kwargs["temperature"] == 0.3
    assert kwargs["max_tokens"] == 1200


def test_mistral_analyze_reads_explicit_file_content_without_llm(tmp_path: Path) -> None:
    target = tmp_path / "README-PYPI.md"
    target.write_text("hello from pypi readme", encoding="utf-8")

    fake_client = Mock()
    with patch("codedjinn.providers.mistral.get_cached_client", return_value=fake_client):
        agent = MistralAgent(api_key="test", model="mistral-small-latest", use_cache=True)
        result = agent.analyze(
            "can you /search what is the content of README-PYPI.md",
            context={"cwd": tmp_path, "os_name": "macOS", "shell": "zsh"},
            previous_context=None,
        )

    fake_client.chat.complete.assert_not_called()
    assert result["answer"] == "README-PYPI.md:\n\nhello from pypi readme"
    assert result["tool_calls"][0]["tool"] == "read_file"


def test_mistral_analyze_does_not_short_circuit_reference_questions(tmp_path: Path) -> None:
    target = tmp_path / "README-PYPI.md"
    target.write_text("hello from pypi readme", encoding="utf-8")

    fake_response = Mock()
    fake_message = Mock()
    fake_message.content = "README-PYPI.md is referenced in docs/index.md"
    fake_message.tool_calls = None
    fake_response.choices = [Mock(message=fake_message)]

    fake_client = Mock()
    fake_client.chat.complete = Mock(return_value=fake_response)
    with patch("codedjinn.providers.mistral.get_cached_client", return_value=fake_client):
        agent = MistralAgent(api_key="test", model="mistral-small-latest", use_cache=True)
        result = agent.analyze(
            "show me where README-PYPI.md is referenced",
            context={"cwd": tmp_path, "os_name": "macOS", "shell": "zsh"},
            previous_context=None,
        )

    fake_client.chat.complete.assert_called_once()
    assert result["answer"] == "README-PYPI.md is referenced in docs/index.md"
    assert result["tool_calls"] == []
