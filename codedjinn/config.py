import os
import configparser
from pathlib import Path
from dotenv import dotenv_values, set_key
from .utils import print_text
from typing import Dict, Tuple, Optional, Any


class ConfigManager:
    """
    Manages configuration for the CodeDjinn application.
    Handles loading, saving, and validating configuration from both
    CFG and .env files.
    """

    def __init__(self) -> None:
        """Initialize the configuration manager"""
        # App directory for .env file (legacy support)
        app_dir = os.path.dirname(os.path.dirname(__file__))
        self.env_path = Path(app_dir) / ".env"

        # User config directory
        user_config_dir = Path.home() / ".config" / "codedjinn"
        self.config_file = user_config_dir / "config.cfg"

        # API key mapping
        self.api_key_map = {
            "deepinfra": "DEEPINFRA_API_TOKEN",
            "mistralai": "MISTRAL_API_KEY",
            "gemini": "GEMINI_API_KEY",
        }

        # Cache for configuration
        self._config_cache = None

    def load_config(self, use_cache: bool = True) -> Dict[str, str]:
        """
        Load configuration from either ~/.config/codedjinn/config.cfg or .env

        Args:
            use_cache: Whether to use cached config if available

        Returns:
            Dict containing configuration values
        """
        # Return cached config if available and requested
        if use_cache and self._config_cache is not None:
            return self._config_cache

        config_dict = {}

        # Try to load from config.cfg first
        if self.config_file.exists():
            try:
                config = configparser.ConfigParser()
                config.read(self.config_file)

                # Extract values from the [DEFAULT] section
                if "DEFAULT" in config:
                    for key, value in config["DEFAULT"].items():
                        config_dict[key.upper()] = value

                # Extract values from the [API_KEYS] section
                if "API_KEYS" in config:
                    for key, value in config["API_KEYS"].items():
                        config_dict[key.upper()] = value

                self._config_cache = config_dict
                return config_dict
            except Exception as e:
                print_text(f"Error loading config from {self.config_file}: {e}", "red")

        # Fall back to .env if available
        if self.env_path.exists():
            try:
                self._config_cache = dotenv_values(self.env_path)
                return self._config_cache
            except Exception as e:
                print_text(f"Error loading config from {self.env_path}: {e}", "red")

        # No config found
        self._config_cache = {}
        return self._config_cache

    def save_config(self, config: Dict[str, str]) -> bool:
        """
        Save configuration to ~/.config/codedjinn/config.cfg

        Args:
            config: Dict containing configuration values

        Returns:
            bool: True if save was successful, False otherwise
        """
        # Create directory if it doesn't exist
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            cfg = configparser.ConfigParser()

            # Add default section for general settings
            cfg["DEFAULT"] = {
                "OS": config.get("OS", ""),
                "OS_FULLNAME": config.get("OS_FULLNAME", ""),
                "SHELL": config.get("SHELL", ""),
                "SHELL_PATH": config.get("SHELL_PATH", ""),
                "LLM_PROVIDER": config.get("LLM_PROVIDER", ""),
                "LLM_MODEL": config.get("LLM_MODEL", ""),
                "SYSTEM_PROMPT_PREFERENCES": config.get("SYSTEM_PROMPT_PREFERENCES", ""),
            }

            # Add API keys section
            cfg["API_KEYS"] = {}
            for provider, key_name in self.api_key_map.items():
                if key_name in config:
                    cfg["API_KEYS"][key_name] = config[key_name]

            # Write to file
            with open(self.config_file, "w") as f:
                cfg.write(f)

            print_text(f"Config file saved at {self.config_file}", "green")

            # Update cache
            self._config_cache = config
            return True
        except Exception as e:
            print_text(f"Error saving config to {self.config_file}: {e}", "red")
            return False

    def update_legacy_config(self, config: Dict[str, str]) -> bool:
        """
        Update the legacy .env file if it exists

        Args:
            config: Dict containing configuration values

        Returns:
            bool: True if update was successful, False otherwise
        """
        if self.env_path.exists():
            try:
                print_text(f"Also updating legacy config at {self.env_path}", "blue")
                for key, value in config.items():
                    set_key(self.env_path, key, value)
                return True
            except Exception as e:
                print_text(f"Error updating legacy config: {e}", "red")
                return False
        return False

    def get_api_key_name(self, provider: str) -> Optional[str]:
        """
        Get the API key name for a given provider

        Args:
            provider: The LLM provider name

        Returns:
            str: The environment variable name for the provider's API key
        """
        return self.api_key_map.get(provider.lower())

    def validate_config(
        self, config: Optional[Dict[str, str]] = None, check_api_key: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate the configuration

        Args:
            config: Dict containing configuration values (loads from file if None)
            check_api_key: Whether to check for API key presence

        Returns:
            tuple: (is_valid, error_message)
        """
        if config is None:
            config = self.load_config()

        # Check for required config values
        required_keys = ["OS_FULLNAME", "SHELL", "LLM_PROVIDER", "LLM_MODEL"]
        missing_keys = [
            key for key in required_keys if key not in config or not config[key]
        ]

        if missing_keys:
            return False, f"Missing configuration values: {', '.join(missing_keys)}"

        # Check for API key if required
        if check_api_key:
            provider = config["LLM_PROVIDER"].lower()
            api_key_name = self.get_api_key_name(provider)

            if api_key_name not in config or not config[api_key_name]:
                return False, f"Missing API key for {provider}"

        return True, None

    def clear_cache(self) -> None:
        """Clear the configuration cache"""
        self._config_cache = None
