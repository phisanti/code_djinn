#!/usr/bin/env python3
"""
High-performance main entry point for CodeDjinn CLI.
Optimized for minimal startup time and maximum responsiveness.
"""


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
    from .parser_config import init
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


def handle_run(wish: str, explain: bool, verbose: bool):
    """Handle run command - direct execution with dangerous command checks."""
    execution_mode = _create_execution_mode()
    if execution_mode:
        execution_mode.execute_safe_command(wish, explain, verbose)


def handle_execute(wish: str, explain: bool, verbose: bool):
    """Handle execute command."""
    execution_mode = _create_execution_mode()
    if execution_mode:
        execution_mode.execute_with_confirmation(wish, explain, verbose)


def _create_execution_mode():
    """
    Factory function to create ExecutionMode instance with proper configuration.
    
    Returns:
        ExecutionMode instance or None if configuration is invalid
    """
    from .config import ConfigManager
    from .core.djinn import Djinn
    from .modes.execution_mode import ExecutionMode
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
            return None

        # Get the API key
        provider = config["LLM_PROVIDER"].lower()
        api_key_name = config_manager.get_api_key_name(provider)

        # Create djinn and then ExecutionMode
        djinn = Djinn.from_config(config, config[api_key_name])
        llm = djinn._get_llm()
        
        # Create ExecutionMode directly
        execution_mode = ExecutionMode(
            llm, 
            djinn.provider, 
            djinn.os_fullname, 
            djinn.shell, 
            djinn.system_prompt_preferences, 
            djinn.shell_path
        )
        
        return execution_mode

    except Exception as e:
        print_text(f"Error: {e}", "red")
        return None


def code_djinn():
    """Main entry point for backward compatibility."""
    fast_djinn_main()


def fast_djinn_main():
    """
    Ultra-fast main entry point with delayed imports and aggressive optimization.
    """
    from .parser import create_parser
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
    elif args.run is not None:
        wish = args.run or input("What do you want to do? ")
        handle_run(wish, args.explain, args.verbose)
    elif args.execute is not None:
        wish = args.execute or input("What do you want to do? ")
        handle_execute(wish, args.explain, args.verbose)
    else:
        print("Command not recognized. Please use --help for available options.")


if __name__ == "__main__":
    fast_djinn_main()