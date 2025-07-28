#!/usr/bin/env python3
"""
High-performance main entry point for CodeDjinn CLI.
Optimized for minimal startup time and maximum responsiveness.
"""

import sys
import argparse
from typing import List, Any, Optional


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser with minimal imports."""
    parser = argparse.ArgumentParser(
        prog="code_djinn", description="An AI CLI assistant"
    )
    parser.add_argument(
        "-i", "--init", action="store_true", help="Initialize the configuration"
    )
    parser.add_argument(
        "-a",
        "--ask",
        metavar="WISH",
        type=str,
        nargs="?",
        const="",
        help="Get a shell command for the given wish",
    )
    parser.add_argument(
        "-t",
        "--test",
        metavar="WISH",
        type=str,
        nargs="?",
        const="",
        help="Test the prompt for the given wish",
    )
    parser.add_argument(
        "-e",
        "--explain",
        action="store_true",
        default=False,
        help="Also provide an explanation for the command",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Verbose output from AI",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available models for all providers",
    )
    parser.add_argument(
        "-x",
        "--execute",
        metavar="WISH",
        type=str,
        nargs="?",
        const="",
        help="Generate and execute a shell command for the given wish",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear LLM client cache for troubleshooting",
    )
    return parser


def handle_clear_cache():
    """Handle cache clearing command."""
    # Import only when needed
    from .core.llm_cache import clear_llm_cache
    from .utils import print_text
    
    clear_llm_cache()
    print_text("✓ LLM client cache cleared", "green")


def handle_list_models():
    """Handle model listing command."""
    # Import only when needed
    from .llmfactory import LLMFactory
    from .utils import print_text
    
    factory = LLMFactory()
    print_text("Available models by provider:", "green")
    
    for provider in factory.get_available_providers():
        print_text(f"\nProvider: {provider}", "blue")
        models = factory.get_available_models(provider)
        if models:
            print_text("Available models:", "yellow")
            model_list = " | ".join(
                [f"{i + 1}. {model}" for i, model in enumerate(models)]
            )
            print_text(model_list, "pink")
        else:
            print_text("No models available for this provider.", "red")


def handle_init():
    """Handle initialization command."""
    # Import only when needed - these are the expensive imports
    init()


def handle_ask(wish: str, explain: bool, verbose: bool):
    """Handle ask command with high performance."""
    # Minimal imports for maximum speed
    from .config import ConfigManager
    from .core.djinn import Djinn
    from .utils import print_text
    
    try:
        # Fast config loading
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        # Validate configuration
        is_valid, error_msg = config_manager.validate_config(config)
        if not is_valid:
            print_text(f"Error: {error_msg}", "red")
            print_text(
                "Please run 'code_djinn --init' to set up your configuration.", "red"
            )
            return
        
        # Get API key
        provider = config["LLM_PROVIDER"].lower()
        api_key_name = config_manager.get_api_key_name(provider)
        
        # Create fast djinn instance
        djinn = Djinn.from_config(config, config[api_key_name])
        
        # Get command (uses cached LLM for speed)
        command, description = djinn.ask(wish, explain, verbose)
        
        # Display results
        if command:
            print()
            print_text(command, "blue")
        if description:
            print_text(f"\nDescription: {description}", "pink")
            
    except Exception as e:
        print_text(f"Error: {e}", "red")


def handle_test(wish: str, explain: bool):
    """Handle test command."""
    from .config import ConfigManager
    from .core.djinn import Djinn
    from .utils import print_text
    
    try:
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        is_valid, error_msg = config_manager.validate_config(config)
        if not is_valid:
            print_text(f"Error: {error_msg}", "red")
            print_text(
                "Please run 'code_djinn --init' to set up your configuration.", "red"
            )
            return
        
        provider = config["LLM_PROVIDER"].lower()
        api_key_name = config_manager.get_api_key_name(provider)
        
        djinn = Djinn.from_config(config, config[api_key_name])
        prompt = djinn.test_prompt(wish, explain)
        
        if prompt:
            print()
            print_text(prompt, "blue")
            
    except Exception as e:
        print_text(f"Error: {e}", "red")


def handle_execute(wish: str, explain: bool, verbose: bool):
    """Handle execute command."""
    # Import only when needed
    execute_command(wish, explain, verbose)


def get_user_selection(items: List[Any], prompt: str) -> Optional[Any]:
    """Helper function to display numbered items and get user selection.

    Args:
        items: List of items to display
        prompt: Prompt message for user input

    Returns:
        The selected item from the list, or None if selection fails
    """
    from .utils import print_text
    
    items_list = " | ".join([f"{i + 1}. {item}" for i, item in enumerate(items)])
    print_text(items_list, "blue")

    selection = None
    while selection is None:
        try:
            choice = input(f"\n{prompt}")
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                selection = items[idx]
            else:
                print_text(f"Invalid selection. Please try again.", "red")
        except ValueError:
            print_text("Please enter a number.", "red")
    return selection


def init():
    """
    Initialize the configuration to get the variables os_family, shell and api_key
    """
    from .config import ConfigManager
    from .utils import get_os_info, print_text
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
    print_text("\nSystem Prompt Preferences (optional):", "green")
    print_text("Enter any additional instructions you'd like to include in prompts", "yellow")
    print_text("Example: 'Use colorful command-line tools like lsd, bat, etc. when available'", "yellow")
    system_prompt_prefs = input("System prompt preferences (press Enter to skip): ").strip()

    # Save config
    config = {
        "OS": os_family,
        "OS_FULLNAME": os_fullname,
        "SHELL": shell,
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


def execute_command(wish: str, explain: bool = False, llm_verbose: bool = False):
    """
    Generate and execute a command with user confirmation.

    Args:
        wish: The user's request or command to generate and execute
        explain: Whether to include an explanation of the command
        llm_verbose: Whether to show verbose LLM output
    """
    from .config import ConfigManager
    from .core.djinn import Djinn
    from .utils import print_text
    
    try:
        config_manager = ConfigManager()
        config = config_manager.load_config()

        # Validate configuration
        is_valid, error_msg = config_manager.validate_config(config)
        if not is_valid:
            print_text(f"Error: {error_msg}", "red")
            print_text(
                "Please run 'code_djinn --init' to set up your configuration.", "red"
            )
            return

        # Get the API key
        provider = config["LLM_PROVIDER"].lower()
        api_key_name = config_manager.get_api_key_name(provider)

        # Init djinn
        thedjinn = Djinn.from_config(config, config[api_key_name])

        # Generate and execute command
        command, description, success, stdout, stderr = thedjinn.ask_and_execute(
            wish, explain, llm_verbose
        )

        # Results are already displayed by the execution mode
        # Just indicate final status if verbose or description exists
        if llm_verbose or description:
            if success:
                print_text("\n✓ Command completed successfully", "green")
            else:
                print_text("\n✗ Command execution failed", "red")

    except Exception as e:
        print_text(f"Error: {e}", "red")
        return


def code_djinn():
    """Main entry point for backward compatibility."""
    fast_djinn_main()


def fast_djinn_main():
    """
    Ultra-fast main entry point with delayed imports and aggressive optimization.
    """
    parser = create_parser()
    args = parser.parse_args()
    
    # Handle commands in order of likelihood and performance impact
    if args.clear_cache:
        handle_clear_cache()
    elif args.list_models:
        handle_list_models()
    elif args.init:
        handle_init()
    elif args.ask is not None:
        wish = args.ask or input("What do you want to do? ")
        handle_ask(wish, args.explain, args.verbose)
    elif args.test is not None:
        wish = args.test or input("What do you want to do? ")
        handle_test(wish, args.explain)
    elif args.execute is not None:
        wish = args.execute or input("What do you want to do? ")
        handle_execute(wish, args.explain, args.verbose)
    else:
        print("Command not recognized. Please use --help for available options.")


if __name__ == "__main__":
    fast_djinn_main()