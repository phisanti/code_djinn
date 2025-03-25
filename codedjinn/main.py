import os
import argparse
from .djinn import djinn
from .utils import get_os_info, print_text
from .llmfactory import LLMFactory
from .config import ConfigManager
from typing import List, Any, Optional


def code_djinn():
    """
    Main entry point for the CodeDjinn CLI application.
    Handles command line argument parsing and routing to appropriate functions.
    """

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
        help="Test the promt for the given wish",
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

    # Parse commands
    args = parser.parse_args()

    # Handle listing models
    if args.list_models:
        factory = LLMFactory()
        print_text("Available models by provider:", "green")
        for provider in factory.get_available_providers():
            print_text(f"\nProvider: {provider}", "blue")
            models = factory.get_available_models(provider)
            if models:
                print_text("Available models:", "yellow")
                # Join model names with a separator for clarity
                model_list = " | ".join(
                    [f"{i + 1}. {model}" for i, model in enumerate(models)]
                )
                print_text(model_list, "pink")
            else:
                print_text("No models available for this provider.", "red")

        return

    if args.init:
        init()
    elif args.test is not None:
        explain = args.explain
        verbose = args.verbose

        wish = args.test
        if not wish:
            wish = input("What do you want to do? ")

        test(wish, explain)
    elif args.ask is not None:
        explain = args.explain
        verbose = args.verbose

        wish = args.ask
        if not wish:
            wish = input("What do you want to do? ")

        ask(wish, explain, verbose)
    else:
        print("Command not recognized. Please use --help for available options.")


def get_user_selection(items: List[Any], prompt: str) -> Optional[Any]:
    """Helper function to display numbered items and get user selection.

    Args:
        items: List of items to display
        prompt: Prompt message for user input

    Returns:
        The selected item from the list, or None if selection fails
    """

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

    # Save config
    config = {
        "OS": os_family,
        "OS_FULLNAME": os_fullname,
        "SHELL": shell,
        "LLM_PROVIDER": provider_choice,
        "LLM_MODEL": model_choice,
        api_key_name: api_key,
    }

    print_text("The following configuration will be saved: \n", "red")
    print_text(str(config), "red")
    print("\n")

    # Save to the new config location
    config_manager.save_config(config)

    # For backward compatibility, also save to .env if it exists
    config_manager.update_legacy_config(config)


def ask(wish: str, explain: bool = False, llm_verbose: bool = False):
    """
    Ask the djinn for a command, main tool of the CLI.

    Args:
        wish: The user's request or command to generate
        explain: Whether to include an explanation of the command
        llm_verbose: Whether to show verbose LLM output
    """
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
        thedjinn = djinn(
            os_fullname=config["OS_FULLNAME"],
            shell=config["SHELL"],
            provider=config["LLM_PROVIDER"],
            model=config["LLM_MODEL"],
            api=config[api_key_name],
        )

        # Request command
        command, description = thedjinn.ask(wish, explain, llm_verbose)

        # Deal with response
        if command:
            print("\n")
            print_text(command, "blue")
        if description:
            print_text(f"\nDescription: {description}", "pink")

    except Exception as e:
        print_text(f"Error: {e}", "red")
        return


def test(wish: str, explain: bool = False):
    """
    Test the prompt for a given wish.

    Args:
        wish: The user's request to test
        explain: Whether to include an explanation in the prompt
    """
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

        # Get the appropriate API key based on provider
        provider = config["LLM_PROVIDER"].lower()
        api_key_name = config_manager.get_api_key_name(provider)

        thedjinn = djinn(
            os_fullname=config["OS_FULLNAME"],
            shell=config["SHELL"],
            provider=config["LLM_PROVIDER"],
            model=config["LLM_MODEL"],
            api=config[api_key_name],
        )

        promt = thedjinn.test_prompt(wish, explain)

        if promt:
            print("\n")
            print_text(promt, "blue")

    except Exception as e:
        print_text(f"Error: {e}", "red")
        return


if __name__ == "__main__":
    code_djinn()
