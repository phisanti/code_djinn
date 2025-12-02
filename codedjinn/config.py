import os
import configparser
from pathlib import Path
from dotenv import dotenv_values, set_key
from .ui.output import UIManager
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

        # UI manager for output
        self.ui = UIManager()

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
                self.ui.error(f"Error loading config from {self.config_file}: {e}")

        # Fall back to .env if available
        if self.env_path.exists():
            try:
                env_values = dotenv_values(self.env_path)
                # Normalize .env keys to uppercase for consistency
                config_dict = {key.upper(): value for key, value in env_values.items()}
                self._config_cache = config_dict
                return self._config_cache
            except Exception as e:
                self.ui.error(f"Error loading config from {self.env_path}: {e}")

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
                "SYSTEM_PROMPT_PREFERENCES": config.get(
                    "SYSTEM_PROMPT_PREFERENCES", ""
                ),
                # New Agno configuration fields
                "AGENT_TEMPERATURE": config.get("AGENT_TEMPERATURE", "0.15"),
                "AGENT_MAX_TOKENS": config.get("AGENT_MAX_TOKENS", "1000"),
                "AGENT_TIMEOUT": config.get("AGENT_TIMEOUT", "30"),
                "SAFETY_POLICY": config.get("SAFETY_POLICY", "balanced"),
                "ENABLE_SHELL_TOOLS": config.get("ENABLE_SHELL_TOOLS", "true"),
                "ENABLE_FILESYSTEM_TOOLS": config.get("ENABLE_FILESYSTEM_TOOLS", "true"),
                "ENABLE_GIT_TOOLS": config.get("ENABLE_GIT_TOOLS", "false"),
                "ENABLE_WEB_TOOLS": config.get("ENABLE_WEB_TOOLS", "false"),
                "FILESYSTEM_READONLY": config.get("FILESYSTEM_READONLY", "true"),
            }

            # Add API keys section
            cfg["API_KEYS"] = {}
            for provider, key_name in self.api_key_map.items():
                if key_name in config:
                    cfg["API_KEYS"][key_name] = config[key_name]

            # Write to file
            with open(self.config_file, "w") as f:
                cfg.write(f)

            self.ui.success(f"Config file saved at {self.config_file}")

            # Update cache
            self._config_cache = config
            return True
        except Exception as e:
            self.ui.error(f"Error saving config to {self.config_file}: {e}")
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
                self.ui.info(f"Also updating legacy config at {self.env_path}")
                for key, value in config.items():
                    set_key(self.env_path, key, value)
                return True
            except Exception as e:
                self.ui.error(f"Error updating legacy config: {e}")
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

    # ===== NEW AGNO ARCHITECTURE METHODS =====

    def get_safety_policy(self) -> str:
        """
        Get the configured safety policy.

        Returns:
            Safety policy name (loose, balanced, strict)
        """
        config = self.load_config()
        return config.get("SAFETY_POLICY", "balanced")

    def set_safety_policy(self, policy: str) -> bool:
        """
        Set the safety policy.

        Args:
            policy: Policy name (loose, balanced, strict)

        Returns:
            True if successful, False otherwise
        """
        if policy not in ["loose", "balanced", "strict"]:
            return False

        config = self.load_config()
        config["SAFETY_POLICY"] = policy
        return self.save_config(config)

    def get_agent_config(self) -> Dict[str, Any]:
        """
        Get agent-specific configuration.

        Returns:
            Dictionary with agent configuration
        """
        config = self.load_config()
        return {
            "provider": config.get("LLM_PROVIDER", "gemini"),
            "model": config.get("LLM_MODEL", "gemini-2.5-flash"),
            "temperature": float(config.get("AGENT_TEMPERATURE", "0.15")),
            "max_tokens": int(config.get("AGENT_MAX_TOKENS", "1000")),
            "timeout": int(config.get("AGENT_TIMEOUT", "30")),
        }

    def set_agent_config(self, agent_config: Dict[str, Any]) -> bool:
        """
        Set agent-specific configuration.

        Args:
            agent_config: Dictionary with agent configuration

        Returns:
            True if successful, False otherwise
        """
        config = self.load_config()

        if "provider" in agent_config:
            config["LLM_PROVIDER"] = agent_config["provider"]
        if "model" in agent_config:
            config["LLM_MODEL"] = agent_config["model"]
        if "temperature" in agent_config:
            config["AGENT_TEMPERATURE"] = str(agent_config["temperature"])
        if "max_tokens" in agent_config:
            config["AGENT_MAX_TOKENS"] = str(agent_config["max_tokens"])
        if "timeout" in agent_config:
            config["AGENT_TIMEOUT"] = str(agent_config["timeout"])

        return self.save_config(config)

    def get_tool_config(self) -> Dict[str, Any]:
        """
        Get tool-specific configuration.

        Returns:
            Dictionary with tool configuration
        """
        config = self.load_config()
        return {
            "enable_shell": config.get("ENABLE_SHELL_TOOLS", "true").lower() == "true",
            "enable_filesystem": config.get("ENABLE_FILESYSTEM_TOOLS", "true").lower() == "true",
            "enable_git": config.get("ENABLE_GIT_TOOLS", "false").lower() == "true",
            "enable_web": config.get("ENABLE_WEB_TOOLS", "false").lower() == "true",
            "filesystem_readonly": config.get("FILESYSTEM_READONLY", "true").lower() == "true",
        }

    def set_tool_config(self, tool_config: Dict[str, Any]) -> bool:
        """
        Set tool-specific configuration.

        Args:
            tool_config: Dictionary with tool configuration

        Returns:
            True if successful, False otherwise
        """
        config = self.load_config()

        if "enable_shell" in tool_config:
            config["ENABLE_SHELL_TOOLS"] = str(tool_config["enable_shell"]).lower()
        if "enable_filesystem" in tool_config:
            config["ENABLE_FILESYSTEM_TOOLS"] = str(tool_config["enable_filesystem"]).lower()
        if "enable_git" in tool_config:
            config["ENABLE_GIT_TOOLS"] = str(tool_config["enable_git"]).lower()
        if "enable_web" in tool_config:
            config["ENABLE_WEB_TOOLS"] = str(tool_config["enable_web"]).lower()
        if "filesystem_readonly" in tool_config:
            config["FILESYSTEM_READONLY"] = str(tool_config["filesystem_readonly"]).lower()

        return self.save_config(config)

    def get_agno_config(self) -> Dict[str, Any]:
        """
        Get complete Agno configuration for easy initialization.

        Returns:
            Dictionary with all Agno-related configuration
        """
        base_config = self.load_config()

        return {
            # Base system info
            "OS": base_config.get("OS", ""),
            "OS_FULLNAME": base_config.get("OS_FULLNAME", ""),
            "SHELL": base_config.get("SHELL", ""),
            "SHELL_PATH": base_config.get("SHELL_PATH", ""),

            # LLM configuration
            "LLM_PROVIDER": base_config.get("LLM_PROVIDER", "gemini"),
            "LLM_MODEL": base_config.get("LLM_MODEL", "gemini-2.5-flash"),

            # API keys
            "DEEPINFRA_API_TOKEN": base_config.get("DEEPINFRA_API_TOKEN", ""),
            "MISTRAL_API_KEY": base_config.get("MISTRAL_API_KEY", ""),
            "GEMINI_API_KEY": base_config.get("GEMINI_API_KEY", ""),

            # Agent configuration
            "AGENT_TEMPERATURE": base_config.get("AGENT_TEMPERATURE", "0.15"),
            "AGENT_MAX_TOKENS": base_config.get("AGENT_MAX_TOKENS", "1000"),
            "AGENT_TIMEOUT": base_config.get("AGENT_TIMEOUT", "30"),

            # Safety policy
            "SAFETY_POLICY": base_config.get("SAFETY_POLICY", "balanced"),

            # Tool configuration
            "ENABLE_SHELL_TOOLS": base_config.get("ENABLE_SHELL_TOOLS", "true"),
            "ENABLE_FILESYSTEM_TOOLS": base_config.get("ENABLE_FILESYSTEM_TOOLS", "true"),
            "ENABLE_GIT_TOOLS": base_config.get("ENABLE_GIT_TOOLS", "false"),
            "ENABLE_WEB_TOOLS": base_config.get("ENABLE_WEB_TOOLS", "false"),
            "FILESYSTEM_READONLY": base_config.get("FILESYSTEM_READONLY", "true"),

            # System preferences
            "SYSTEM_PROMPT_PREFERENCES": base_config.get("SYSTEM_PROMPT_PREFERENCES", ""),
        }
