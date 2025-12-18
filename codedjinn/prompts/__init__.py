"""Prompt building and management modules.

This package provides utilities for constructing structured prompts
using XML-like tags following Anthropic's recommendations.
"""

from codedjinn.prompts.system_prompt import (
    build_system_prompt,
    build_agentic_prompt,
    get_system_prompt,
)
from codedjinn.prompts.context_builder import (
    build_system_info,
    build_environment,
    build_command_context,
    build_instructions,
    build_project_context,
    SmartContext,
    ContextDetector,
    get_context_detector,
)
from codedjinn.prompts.parser import (
    escape_xml_content,
    wrap_xml_tag,
    simple_xml_tag,
)
from codedjinn.prompts.step_budget import (
    init_session_state_for_steps,
    advance_step_budget,
    normalize_max_steps,
    refresh_step_context,
)

__all__ = [
    # Main builders
    "build_system_prompt",
    "build_agentic_prompt",
    "get_system_prompt",
    # Component builders
    "build_system_info",
    "build_environment",
    "build_command_context",
    "build_instructions",
    "build_project_context",
    # Smart context detection
    "SmartContext",
    "ContextDetector",
    "get_context_detector",
    # XML utilities
    "escape_xml_content",
    "wrap_xml_tag",
    "simple_xml_tag",
    # Step budget (existing)
    "init_session_state_for_steps",
    "advance_step_budget",
    "normalize_max_steps",
    "refresh_step_context",
]
