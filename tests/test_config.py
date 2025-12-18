"""
Tests for config loading and validation.

The project previously exposed a ConfigManager class. The current implementation
uses lightweight helpers in `codedjinn.core.configs`.
"""

import unittest
import tempfile
from pathlib import Path

from codedjinn.core.configs import get_agent_settings, get_model_config, load_raw_config


class TestConfigManager(unittest.TestCase):
    """Test cases for configuration helpers."""

    def setUp(self):
        """Set up test environment with temporary directories."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "config.cfg"

    def tearDown(self):
        """Clean up temporary files."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_config(self, *, defaults: dict[str, str], api_keys: dict[str, str]) -> None:
        import configparser

        cfg = configparser.ConfigParser()
        cfg["DEFAULT"] = defaults
        cfg["API_KEYS"] = api_keys
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w") as handle:
            cfg.write(handle)

    def test_load_raw_config_lowercases_keys(self):
        self._write_config(
            defaults={"LLM_PROVIDER": "deepinfra", "LLM_MODEL": "QwQ-32B-Preview"},
            api_keys={"DEEPINFRA_API_TOKEN": "test_api_key_123"},
        )

        raw = load_raw_config(self.config_file)
        self.assertEqual(raw["llm_provider"], "deepinfra")
        self.assertEqual(raw["llm_model"], "QwQ-32B-Preview")
        self.assertEqual(raw["deepinfra_api_token"], "test_api_key_123")

    def test_get_model_config_success(self):
        self._write_config(
            defaults={"LLM_PROVIDER": "deepinfra", "LLM_MODEL": "QwQ-32B-Preview"},
            api_keys={"DEEPINFRA_API_TOKEN": "valid_token"},
        )
        raw = load_raw_config(self.config_file)
        model_config = get_model_config(raw)

        self.assertEqual(model_config.provider, "deepinfra")
        self.assertEqual(model_config.model, "QwQ-32B-Preview")
        self.assertEqual(model_config.api_key, "valid_token")

    def test_get_model_config_missing_provider_or_model_raises(self):
        with self.assertRaises(ValueError):
            get_model_config({"llm_provider": "deepinfra"})

        with self.assertRaises(ValueError):
            get_model_config({"llm_model": "QwQ-32B-Preview"})

    def test_get_model_config_missing_api_key_raises(self):
        with self.assertRaises(ValueError) as context:
            get_model_config(
                {"llm_provider": "deepinfra", "llm_model": "QwQ-32B-Preview"}
            )
        self.assertIn("Missing API key", str(context.exception))

    def test_get_model_config_timeout_env_override(self):
        import os
        from unittest.mock import patch

        raw = {
            "llm_provider": "deepinfra",
            "llm_model": "QwQ-32B-Preview",
            "deepinfra_api_token": "valid_token",
            "timeout": "1",
        }

        with patch.dict(os.environ, {"CODEDJINN_AGENT_TIMEOUT_S": "42"}, clear=False):
            model_config = get_model_config(raw)

        self.assertEqual(model_config.timeout, 42)

    def test_get_agent_settings_defaults(self):
        settings = get_agent_settings({})
        self.assertIsInstance(settings.instructions, str)
        self.assertFalse(settings.markdown)
        self.assertFalse(settings.add_history_to_context)

    def test_load_raw_config_missing_file_returns_empty_dict(self):
        self.assertFalse(self.config_file.exists())
        raw = load_raw_config(self.config_file)
        self.assertEqual(raw, {}, "Should return empty dict when config does not exist")

    def test_agent_settings_boolean_parsing(self):
        settings = get_agent_settings(
            {"agent_markdown": "true", "agent_add_history": "1", "agent_instructions": "hi"}
        )
        self.assertTrue(settings.markdown)
        self.assertTrue(settings.add_history_to_context)
        self.assertEqual(settings.instructions, "hi")


if __name__ == "__main__":
    unittest.main()
