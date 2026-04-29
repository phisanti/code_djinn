"""Test session management and output trimming functionality.

Focus on core behaviors:
- Sessions persist command context
- Output trimming handles large outputs
- Integration of both features works correctly
"""

import pytest
from pathlib import Path
from codedjinn.core.session import Session
from codedjinn.tools.output_trimmer import trim_output, estimate_tokens


@pytest.fixture
def test_session():
    """Create a test session and clean it up after test."""
    session = Session("pytest_test_session")
    session.clear()
    yield session
    session.clear()


class TestSessionPersistence:
    """Test that sessions save and load command context."""

    def test_empty_session_returns_no_context(self, test_session):
        """Empty session should return None for context."""
        assert test_session.get_context_for_prompt() is None

    def test_session_saves_and_loads_command(self, test_session):
        """Session should persist command data across save/load."""
        test_session.save("ls -la", "file1.txt\nfile2.txt", 0)

        context = test_session.get_context_for_prompt()
        assert context is not None
        assert context['command'] == "ls -la"
        assert "file1.txt" in context['output']
        assert context['exit_code'] == 0

    def test_session_creates_file_on_disk(self, test_session):
        """Session should create persistent JSON file."""
        test_session.save("echo test", "test", 0)

        assert test_session.session_file.exists()

    def test_cleared_session_removes_context(self, test_session):
        """Clearing session should remove all context."""
        test_session.save("cmd", "output", 0)
        test_session.clear()

        assert test_session.get_context_for_prompt() is None


class TestOutputTrimming:
    """Test output trimming for managing large command outputs."""

    def test_short_output_not_trimmed(self):
        """Short outputs should pass through unchanged."""
        short = "line1\nline2\nline3"
        assert trim_output(short) == short

    def test_empty_output_has_placeholder(self):
        """Empty output should return special message."""
        assert trim_output("") == "(no output)"

    def test_long_output_gets_trimmed(self):
        """Very long output should be truncated with indicator."""
        long_output = "\n".join([f"line{i}" for i in range(100)])
        result = trim_output(long_output, max_lines=30)

        assert "omitted" in result
        assert len(result) < len(long_output)

    def test_token_estimation_returns_positive(self):
        """Token estimator should return reasonable counts."""
        tokens = estimate_tokens("This is a test string")
        assert tokens > 0


class TestSessionWithTrimming:
    """Test integration of session persistence with output trimming."""

    def test_context_available_for_followup_command(self, test_session):
        """Session context should be accessible for subsequent commands."""
        test_session.save("git branch", "* main\n  feature-x", 0)

        context = test_session.get_context_for_prompt()
        assert "feature-x" in context['output']

    def test_long_output_trimmed_before_saving(self, test_session):
        """Long output should be trimmed when saved to session."""
        long_output = "\n".join([f"commit {i}" for i in range(200)])
        trimmed = trim_output(long_output)
        test_session.save("git log", trimmed, 0)

        context = test_session.get_context_for_prompt()
        assert len(context['output']) < len(long_output)
