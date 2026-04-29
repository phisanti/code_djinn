from pathlib import Path
from unittest.mock import Mock, patch

from codedjinn.providers.mistral import MistralAgent


def test_mistral_analyze_does_not_use_tools() -> None:
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
    assert kwargs["tool_choice"] == "any"
    assert kwargs["temperature"] == 0.3
    assert kwargs["max_tokens"] == 4096

