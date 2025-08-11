#!/usr/bin/env python3
"""
Command handlers for CodeDjinn CLI.
Separated from main.py for cleaner architecture and easier testing.
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


def handle_run(wish: str, explain: bool, verbose: bool, no_confirm: bool = False):
    """Handle run command - unified execution with optional confirmation."""
    execution_mode = _create_execution_mode()
    if execution_mode:
        if no_confirm:
            # Use safe command execution (auto-executes safe commands, confirms dangerous ones)
            execution_mode.execute_safe_command(wish, explain, verbose)
        else:
            # Always ask for confirmation (original execute behavior)
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


def handle_chat(session_id: str = ""):
    """Handle chat mode command."""
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
        
        # Start chat mode
        djinn.start_chat(session_id if session_id else None)
            
    except Exception as e:
        print_text(f"Error: {e}", "red")