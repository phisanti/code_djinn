"""Response parser for LLM outputs.

Extracts content and model information from agent responses
Handles both dict and object formats flexibly
"""

from typing import Any, Dict


def _extract_field(obj: Any, field: str) -> Any:
    """Safely extract a field from objects or mappings."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(field)
    return getattr(obj, field, None)


def parse_response(response: Any) -> Dict[str, str]:
    """
    Parse an Agno RunOutput-like response into a minimal dict.

    Returns:
        {"content": <str>, "model": <str>}
    """
    content = _extract_field(response, "content")
    model = _extract_field(response, "model")

    return {
        "content": "" if content is None else str(content),
        "model": "" if model is None else str(model),
    }
