"""
Tests for config.py - Configuration management functionality.

These tests validate the ConfigManager class which handles loading, saving,
and validating configuration for the CodeDjinn application.
"""

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

from codedjinn.config import ConfigManager


class TestConfigManager(unittest.TestCase):
    """Test cases for ConfigManager class."""

    def setUp(self):
        """Set up test environment with temporary directories."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_manager = ConfigManager()

        # Override paths to use temp directory
        self.config_manager.config_file = Path(self.temp_dir) / "config.cfg"
        self.config_manager.env_path = Path(self.temp_dir) / ".env"

    def tearDown(self):
        """Clean up temporary files."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_and_load_config(self):
        """Test saving and loading a complete configuration."""
        # Sample configuration
        test_config = {
            "OS": "MacOS",
            "OS_FULLNAME": "macOS 15.5",
            "SHELL": "fish",
            "SHELL_PATH": "/opt/homebrew/bin/fish",
            "LLM_PROVIDER": "deepinfra",
            "LLM_MODEL": "QwQ-32B-Preview",
            "SYSTEM_PROMPT_PREFERENCES": "Use colorful tools when available",
            "DEEPINFRA_API_TOKEN": "test_api_key_123",
        }

        # Save configuration
        result = self.config_manager.save_config(test_config)
        self.assertTrue(result, "Config save should succeed")

        # Load and verify
        loaded_config = self.config_manager.load_config(use_cache=False)

        # Check that all important fields are preserved
        self.assertEqual(loaded_config["OS"], "MacOS")
        self.assertEqual(loaded_config["SHELL"], "fish")
        self.assertEqual(loaded_config["SHELL_PATH"], "/opt/homebrew/bin/fish")
        self.assertEqual(loaded_config["LLM_PROVIDER"], "deepinfra")
        self.assertEqual(
            loaded_config["SYSTEM_PROMPT_PREFERENCES"],
            "Use colorful tools when available",
        )
        self.assertEqual(loaded_config["DEEPINFRA_API_TOKEN"], "test_api_key_123")

    def test_validate_config_success(self):
        """Test configuration validation with valid config."""
        valid_config = {
            "OS_FULLNAME": "macOS 15.5",
            "SHELL": "fish",
            "LLM_PROVIDER": "deepinfra",
            "LLM_MODEL": "QwQ-32B-Preview",
            "DEEPINFRA_API_TOKEN": "valid_token",
        }

        is_valid, error_msg = self.config_manager.validate_config(valid_config)
        self.assertTrue(is_valid, f"Config should be valid, got error: {error_msg}")
        self.assertIsNone(error_msg)

    def test_validate_config_missing_keys(self):
        """Test configuration validation with missing required keys."""
        incomplete_config = {
            "OS_FULLNAME": "macOS 15.5",
            "SHELL": "fish",
            # Missing LLM_PROVIDER and LLM_MODEL
        }

        is_valid, error_msg = self.config_manager.validate_config(incomplete_config)
        self.assertFalse(is_valid, "Config should be invalid due to missing keys")
        self.assertIn("Missing configuration values", error_msg)
        self.assertIn("LLM_PROVIDER", error_msg)
        self.assertIn("LLM_MODEL", error_msg)

    def test_validate_config_missing_api_key(self):
        """Test configuration validation with missing API key."""
        config_no_api_key = {
            "OS_FULLNAME": "macOS 15.5",
            "SHELL": "fish",
            "LLM_PROVIDER": "deepinfra",
            "LLM_MODEL": "QwQ-32B-Preview",
            # Missing DEEPINFRA_API_TOKEN
        }

        is_valid, error_msg = self.config_manager.validate_config(config_no_api_key)
        self.assertFalse(is_valid, "Config should be invalid due to missing API key")
        self.assertIn("Missing API key for deepinfra", error_msg)

    def test_get_api_key_name(self):
        """Test API key name retrieval for different providers."""
        self.assertEqual(
            self.config_manager.get_api_key_name("deepinfra"), "DEEPINFRA_API_TOKEN"
        )
        self.assertEqual(
            self.config_manager.get_api_key_name("mistralai"), "MISTRAL_API_KEY"
        )
        self.assertEqual(
            self.config_manager.get_api_key_name("gemini"), "GEMINI_API_KEY"
        )
        self.assertIsNone(self.config_manager.get_api_key_name("unknown_provider"))

    def test_load_config_empty_returns_empty_dict(self):
        """Test that loading non-existent config returns empty dict."""
        # Ensure no config files exist
        self.assertFalse(self.config_manager.config_file.exists())
        self.assertFalse(self.config_manager.env_path.exists())

        loaded_config = self.config_manager.load_config(use_cache=False)
        self.assertEqual(
            loaded_config, {}, "Should return empty dict when no config exists"
        )

    def test_clear_cache(self):
        """Test cache clearing functionality."""
        # Load config to populate cache
        self.config_manager._config_cache = {"test": "data"}

        # Clear cache
        self.config_manager.clear_cache()

        # Verify cache is cleared
        self.assertIsNone(self.config_manager._config_cache)


if __name__ == "__main__":
    unittest.main()
