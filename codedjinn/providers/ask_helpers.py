"""Ask-mode helpers that keep provider classes focused on API orchestration.

The functions here are provider-neutral. They handle deterministic request
processing that should not require an LLM round trip, plus compatibility
formatting for older multi-step tests.
"""

import re
from typing import Any

from codedjinn.context.parser import escape_xml_content
from codedjinn.tools.ask_executor import AskToolExecutor


CONTENT_INTENTS = (
    "content of",
    "contents of",
    "what is in",
    "what's in",
)
DIRECT_READ_VERBS = ("read", "show", "display", "cat", "open")
# These terms usually mean "find references or locations" rather than "show the
# literal file body". Keeping them separate avoids turning search questions into
# direct reads just because the user used the word "show".
LOCATION_INTENTS = (
    " where ",
    "referenc",
    "which file",
    "contains",
    "has ",
    "find ",
    "search ",
)
FILE_PATH_PATTERN = re.compile(
    r"(?<!\w)((?:~?/|\./|\../)?[A-Za-z0-9_.@%+=:,/-]+\.[A-Za-z0-9][A-Za-z0-9._-]*)"
)


def maybe_answer_file_content_question(
    question: str,
    file_executor: AskToolExecutor,
) -> dict[str, Any] | None:
    """Answer explicit file-content questions without calling the model.

    This fast path exists for requests such as "what is the content of
    README.md" where the user has already provided the exact file. It saves
    latency and prevents the model from incorrectly claiming a present file is
    missing.

    Reference/location questions intentionally fall through to normal ask
    tooling. For example, "show me where README.md is referenced" needs a repo
    search, not a direct README read.
    """
    path = _last_explicit_path(question)
    if path is None or not _is_direct_file_read(question, path):
        return None

    content = file_executor.execute_read_file(path)
    if content.startswith("Error:"):
        return None

    return {
        "answer": f"{path}:\n\n{content}",
        "tool_calls": [{
            "tool": "read_file",
            "path": path,
            "context": "explicit file content request",
            "output": content[:200] + "..." if len(content) > 200 else content,
        }],
    }


def _last_explicit_path(question: str) -> str | None:
    """Return the last filename/path-like token in a user question."""
    matches = FILE_PATH_PATTERN.findall(question)
    if not matches:
        return None
    return matches[-1].rstrip(".,:;)")


def _is_direct_file_read(question: str, path: str) -> bool:
    """Decide whether a question asks for file contents, not references."""
    lowered = question.lower()
    content_intent = any(intent in lowered for intent in CONTENT_INTENTS)
    if any(needle in lowered for needle in LOCATION_INTENTS) and not content_intent:
        return False
    return content_intent or _read_verb_targets_path(lowered, path)


def _read_verb_targets_path(lowered_question: str, path: str) -> bool:
    """Check direct read verbs that syntactically target the detected path."""
    path_pattern = re.escape(path).lower()
    verb_pattern = "|".join(DIRECT_READ_VERBS)
    direct_read_pattern = (
        rf"\b(?:{verb_pattern})\b"
        rf"(?:\s+(?:me|the|file|contents?|of))*\s+{path_pattern}"
    )
    return re.search(direct_read_pattern, lowered_question) is not None


def format_observations_xml(observations: list[dict[str, Any]]) -> str:
    """Render observations as XML for legacy prompt/test compatibility.

    Multi-step ask now keeps tool output in the model message chain. This
    formatter remains as a stable compatibility surface for older tests and any
    caller that still builds prompt fragments from observations.
    """
    if not observations:
        return ""

    lines = ["<prior_observations>"]
    for obs in observations:
        step = obs.get("step", "")
        tool = escape_xml_content(str(obs.get("tool", "")))
        path = escape_xml_content(str(obs.get("path", "")))
        context = escape_xml_content(str(obs.get("context", "")))
        result = str(obs.get("result", ""))
        if len(result) > 500:
            result = result[:500] + "\n[... file truncated ...]"
        result = escape_xml_content(result)

        lines.append(f'  <observation step="{step}" tool="{tool}">')
        if path:
            lines.append(f"    <path>{path}</path>")
        if context:
            lines.append(f"    <context>{context}</context>")
        lines.append(f"    <result>{result}</result>")
        lines.append("  </observation>")
    lines.append("</prior_observations>")
    return "\n".join(lines)


def format_observations_for_synthesis(observations: list[dict[str, Any]]) -> str:
    """Render observations as compact text for fallback answer synthesis."""
    if not observations:
        return ""

    chunks = []
    for obs in observations:
        tool = obs.get("tool", "unknown")
        path = obs.get("path", "")
        command = obs.get("command", "")
        context = obs.get("context", "")
        result = str(obs.get("result", ""))
        if len(result) > 800:
            result = result[:800] + "\n[... content truncated ...]"

        if tool == "read_file":
            heading = f"[File: {path}]"
        elif tool == "execute_observe_command":
            heading = f"[Command: {command}]"
        else:
            heading = f"[{tool}]"

        if context:
            chunks.append(f"{heading}\nReason: {context}\n{result}")
        else:
            chunks.append(f"{heading}\n{result}")

    return "\n\n".join(chunks)
