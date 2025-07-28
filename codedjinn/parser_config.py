#!/usr/bin/env python3
"""
Configuration initialization module for CodeDjinn CLI.
Handles the interactive configuration setup process.
"""

from typing import Optional
from .parser import get_user_selection


def init():
    """
    Initialize the configuration to get the variables os_family, shell and api_key
    """
    from .config import ConfigManager
    from .utils import get_os_info, print_text, get_shell_path
    from .llmfactory import LLMFactory
    import os
    
    config_manager = ConfigManager()

    os_family, os_fullname = get_os_info()

    if os_family:
        print_text(f"Detected OS: {os_fullname} \n", color="green")
        answer = input(f"Type yes to confirm or no to input manually: ")
        if answer.lower() in ("yes", "y"):
            pass
        else:
            os_family = input("What is your OS family? (e.g. Windows, MacOS, Linux): ")

    # Initialize shell with a default value
    shell = "bash"

    if os_family in ("Linux", "MacOS"):
        shell_str = os.environ.get("SHELL", "")
        if "bash" in shell_str:
            shell = "bash"
        elif "zsh" in shell_str:
            shell = "zsh"
        elif "fish" in shell_str:
            shell = "fish"
        else:
            shell = input("What shell are you using? (default: bash) ") or "bash"
    
    # Detect shell path once during configuration
    shell_path = get_shell_path(shell)
    if not shell_path:
        print_text(f"Warning: Could not find {shell} executable in PATH. Command execution may fall back to default shell.", "yellow")
        shell_path = ""

    # Get LLM provider and model
    factory = LLMFactory()
    providers = factory.get_available_providers()

    print_text("\nAvailable LLM providers:", "green")
    provider_choice = get_user_selection(providers, "Select a provider (number): ")

    models = factory.get_available_models(provider_choice)
    print_text(f"\nAvailable models for {provider_choice}:", "green")
    model_choice = get_user_selection(models, "Select a model (number): ")

    # Get API key based on selected provider
    api_key_name = config_manager.get_api_key_name(provider_choice)
    api_key = input(f"What is your {provider_choice} API key? ")

    # Get system prompt preferences
    print_text("\nSystem Prompt Preferences (optional):\n", "green")
    print_text("Enter any additional instructions you'd like to include in prompts\n", "yellow")
    print_text("Example: 'Use colorful command-line tools like lsd, bat, etc. when available'\n", "yellow")
    system_prompt_prefs = input("System prompt preferences (press Enter to skip): ").strip()

    # Save config
    config = {
        "OS": os_family,
        "OS_FULLNAME": os_fullname,
        "SHELL": shell,
        "SHELL_PATH": shell_path,
        "LLM_PROVIDER": provider_choice,
        "LLM_MODEL": model_choice,
        "SYSTEM_PROMPT_PREFERENCES": system_prompt_prefs,
        api_key_name: api_key,
    }

    print_text("The following configuration will be saved: \n", "red")
    print_text(str(config), "red")
    print("\n")

    # Save to the new config location
    config_manager.save_config(config)

    # For backward compatibility, also save to .env if it exists
    config_manager.update_legacy_config(config)