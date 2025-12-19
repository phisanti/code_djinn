"""Configuration management for Code Djinn.

Loads user settings from ~/.config/codedjinn/config.cfg
Provides ModelConfig (LLM settings) and AgentSettings (agent behavior)
"""

import configparser
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Dict, Optional

# Default location for user configuration (legacy compatible).
CONFIG_PATH = Path.home() / ".config" / "codedjinn" / "config.cfg"


@dataclass
class ModelConfig:
    provider: str
    model: str
    api_key: str
    temperature: float = 0.2
    max_tokens: int = 512
    timeout: int = 30


@dataclass
class AgentSettings:
    instructions: str = "You are Code Djinn. Reply with: Hello world."
    markdown: bool = False
    add_history_to_context: bool = False


def load_raw_config(path: Path = CONFIG_PATH) -> Dict[str, str]:
    """
    Load configuration values from the standard config path.
    Values are returned with lowercase keys for convenience.
    """
    cfg = configparser.ConfigParser()
    data: Dict[str, str] = {}

    if path.exists():
        cfg.read(path)
        if "DEFAULT" in cfg:
            data.update({k.lower(): v for k, v in cfg["DEFAULT"].items()})
        if "API_KEYS" in cfg:
            data.update({k.lower(): v for k, v in cfg["API_KEYS"].items()})

    return data


def _get_bool(raw: Dict[str, str], key: str, default: bool = False) -> bool:
    value = raw.get(key, "")
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def get_model_config(raw: Optional[Dict[str, str]] = None) -> ModelConfig:
    """
    Build a ModelConfig from raw configuration values.
    Raises ValueError if required fields are missing.
    """
    raw = raw or load_raw_config()

    provider = raw.get("llm_provider", "").strip().lower()
    model = raw.get("llm_model", "").strip()
    if not provider or not model:
        raise ValueError("Missing LLM provider or model in configuration.")

    api_key_map = {
        "mistralai": "mistral_api_key",
        "gemini": "gemini_api_key",
        "deepinfra": "deepinfra_api_token",
    }
    key_name = api_key_map.get(provider)
    api_key = raw.get(key_name or "", "").strip()
    if not api_key:
        raise ValueError(
            f"Missing API key for provider '{provider}'. Expected key '{key_name}'."
        )

    temperature = float(raw.get("agent_temperature", raw.get("temperature", 0.2) or 0.2))
    max_tokens = int(
        float(raw.get("agent_max_tokens", raw.get("max_tokens", 512) or 512))
    )
    timeout_env = os.environ.get("CODEDJINN_AGENT_TIMEOUT_S") or os.environ.get("CODEDJINN_LLM_TIMEOUT_S")
    if timeout_env is not None and str(timeout_env).strip() != "":
        timeout = int(float(timeout_env))
    else:
        timeout = int(float(raw.get("agent_timeout", raw.get("timeout", 30) or 30)))

    return ModelConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )


def get_agent_settings(raw: Optional[Dict[str, str]] = None) -> AgentSettings:
    """Extract agent-specific settings from the raw config."""
    raw = raw or load_raw_config()
    return AgentSettings(
        instructions=raw.get(
            "agent_instructions", "You are Code Djinn. Reply with: Hello world."
        ),
        markdown=_get_bool(raw, "agent_markdown", False),
        add_history_to_context=_get_bool(raw, "agent_add_history", False),
    )
