"""
Step-budget prompt steering utilities.

This module is intentionally lightweight: it only manages a small session_state
shape that is appended to the system message (when enabled) so the model sees:
- The current step k/N
- Remaining steps
- A per-step instruction string (with urgency on the final step)
"""


def normalize_max_steps(max_steps: int | None) -> int | None:
    if max_steps is None:
        return None
    try:
        value = int(max_steps)
    except (TypeError, ValueError):
        return None
    # Allow 0 as a sentinel for "fast" execution mode.
    return max(0, value)


def _build_step_instruction(*, current_step: int, max_steps: int) -> str:
    if current_step >= max_steps:
        return (
            f"META: Final step ({max_steps}/{max_steps}). "
            "This is the last allowed tool call. "
            "Use exec_shell to execute the best single shell command now. "
            "No deferral, no placeholders. If assumptions are needed, state them briefly and proceed."
        )

    remaining = max_steps - current_step
    return (
        f"META: Step {current_step}/{max_steps}. Remaining steps after this: {remaining}. "
        "Finish as early as possible. Minimize tool calls. Plan to use exec_shell on the final step."
    )


def refresh_step_context(session_state: dict) -> None:
    """
    Refresh derived fields based on max_steps/tool_calls_used.

    Expected shape:
        session_state["step_budget"] = {"max_steps": int, "tool_calls_used": int}
    """
    step_budget = session_state.get("step_budget") or {}
    max_steps = int(step_budget.get("max_steps") or 1)
    tool_calls_used = int(step_budget.get("tool_calls_used") or 0)

    current_step = min(max_steps, tool_calls_used + 1)
    session_state["step_context"] = {
        "current_step": current_step,
        "max_steps": max_steps,
        "remaining_steps": max_steps - current_step,
        "is_final_step": current_step >= max_steps,
        "instruction": _build_step_instruction(current_step=current_step, max_steps=max_steps),
    }


def init_session_state_for_steps(max_steps: int) -> dict:
    max_steps = normalize_max_steps(max_steps) or 1
    session_state: dict = {"step_budget": {"max_steps": max_steps, "tool_calls_used": 0}}
    refresh_step_context(session_state)
    return session_state


def advance_step_budget(session_state: dict, *, tool_calls: int = 1) -> None:
    """
    Advance the budget after a tool call so the next model turn sees a new step.
    """
    step_budget = session_state.setdefault("step_budget", {})
    used = int(step_budget.get("tool_calls_used") or 0)
    step_budget["tool_calls_used"] = used + max(1, int(tool_calls))
    refresh_step_context(session_state)
