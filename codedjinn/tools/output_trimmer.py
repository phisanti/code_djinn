"""Intelligent output trimming for token budget management."""


def trim_output(output: str, max_lines: int = 30, max_chars: int = 2000) -> str:
    """
    Intelligently trim command output to fit token budget.

    Strategy:
    1. If output is small enough, return as-is
    2. Keep first 15 lines (context start - often most important)
    3. Keep last 10 lines (most recent info, errors often at end)
    4. Summarize middle with line count

    Special cases:
    - If output contains "error" or "Error", keep all error context
    - Empty output returns "(no output)"

    Args:
        output: Raw command output (stdout + stderr)
        max_lines: Maximum lines to keep (default: 30)
        max_chars: Maximum characters to keep (default: 2000)

    Returns:
        Trimmed output string

    Example:
        >>> trim_output("line1\\nline2\\n...100 lines...\\nline100", max_lines=10)
        'line1\\nline2\\n...\\n(85 lines omitted)\\n...\\nline99\\nline100'
    """
    if not output or output.isspace():
        return "(no output)"

    # If output is already small, return as-is
    if len(output) <= max_chars and output.count('\n') <= max_lines:
        return output

    # Check for errors - keep full error context
    if 'error' in output.lower() or 'exception' in output.lower():
        # Still enforce char limit but be more generous with lines
        if len(output) <= max_chars * 2:
            return output

    lines = output.split('\n')
    total_lines = len(lines)

    # If line count is manageable but chars exceed limit
    if total_lines <= max_lines:
        truncated_length = len(output) - max_chars
        return output[:max_chars] + f"\n\n(truncated - {truncated_length} chars omitted)"

    # Keep first 15 and last 10 lines
    keep_first = 15
    keep_last = 10
    omitted = total_lines - keep_first - keep_last

    if omitted > 0:
        trimmed_lines = (
            lines[:keep_first] +
            [f"\n... ({omitted} lines omitted) ...\n"] +
            lines[-keep_last:]
        )
    else:
        trimmed_lines = lines

    result = '\n'.join(trimmed_lines)

    # Final char limit check
    if len(result) > max_chars:
        truncated_length = len(result) - max_chars
        result = result[:max_chars] + f"\n\n(truncated - {truncated_length} chars omitted)"

    return result


def estimate_tokens(text: str) -> int:
    """
    Rough token estimation (4 chars ≈ 1 token for English).

    Used for quick checks before API calls. Actual tokenization
    happens on Mistral's side.

    Args:
        text: Input text

    Returns:
        Estimated token count
    """
    return len(text) // 4
