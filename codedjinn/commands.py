#!/usr/bin/env python3
"""
Command handlers for CodeDjinn CLI using Agno architecture.
Clean, fast, and with the over-zealous safety bug FIXED!
"""

import sys
from typing import Optional
from .config import ConfigManager
from .core.tool_registry import ToolRegistry
from .core.agent_service import AgentService
from .core.policy_engine import PolicyEngine
from .modes.run_mode import RunMode
from .ui.output import UIManager
from .ui.prompts import PromptManager
from .utils import get_shell_path


def handle_run(
    wish: str,
    explain: bool = False,
    verbose: bool = False,
    no_confirm: bool = False,
) -> None:
    """
    Handle run command using new Agno architecture.
    
    This is THE CORE BUG FIX implementation!
    
    Args:
        wish: User's natural language request
        explain: Include explanation of command
        verbose: Show detailed output
        no_confirm: Skip confirmation for ALLOW-level commands
    """
    ui = UIManager()
    
    try:
        if verbose:
            ui.info("🚀 Starting Code Djinn with Agno architecture")
        
        # Load configuration
        config_manager = ConfigManager()
        config = config_manager.get_agno_config()
        
        # Validate configuration
        is_valid, error = config_manager.validate_config(config)
        if not is_valid:
            ui.error(f"❌ Configuration error: {error}")
            ui.info("💡 Run 'code-djinn --init' to set up configuration")
            sys.exit(1)
        
        if verbose:
            ui.info(f"📋 Using {config['LLM_PROVIDER']} with {config['LLM_MODEL']}")
            ui.info(f"🛡️  Safety policy: {config['SAFETY_POLICY']}")
        
        # Initialize components
        tool_registry = ToolRegistry(config)
        agent_service = AgentService(config, tool_registry)
        policy_engine = PolicyEngine(config["SAFETY_POLICY"])
        prompt_manager = PromptManager()
        
        # Get shell path
        shell_path = get_shell_path(config.get("SHELL", ""))
        
        # Create run mode
        run_mode = RunMode(
            agent_service=agent_service,
            policy_engine=policy_engine,
            ui=ui,
            prompt_manager=prompt_manager,
            shell_path=shell_path,
        )
        
        # Execute the request
        success = run_mode.execute_request(
            wish=wish,
            explain=explain,
            verbose=verbose,
            no_confirm=no_confirm,
        )
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        ui.warning("\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        ui.error(f"❌ Unexpected error: {str(e)}")
        if verbose:
            import traceback
            ui.dim(traceback.format_exc())
        sys.exit(1)


def handle_chat(session_id: Optional[str] = None) -> None:
    """
    Handle chat command using new Agno architecture.
    
    Args:
        session_id: Optional session identifier
    """
    ui = UIManager()
    ui.info("🚧 Chat mode with Agno architecture is not yet implemented")
    ui.info("💡 This will be added in Phase 2 of the migration")
    ui.info("🔄 For now, use the run mode: code-djinn --run 'your request'")


def handle_init() -> None:
    """
    Handle initialization using new Agno architecture.
    """
    ui = UIManager()
    ui.info("🚧 Agno-based initialization is not yet implemented")
    ui.info("💡 For now, use the existing initialization: code-djinn --init")


def handle_list_models() -> None:
    """
    Handle list models using new Agno architecture.
    """
    ui = UIManager()
    
    # Show available models for each provider
    models = {
        "gemini": [
            "gemini-2.5-flash",
            "gemini-2.0-flash-exp",
            "gemini-1.5-pro",
        ],
        "mistralai": [
            "codestral-latest",
            "mistral-small-latest",
            "mistral-large-latest",
        ],
        "deepinfra": [
            "Qwen/QwQ-32B-Preview",
            "Qwen/Qwen2.5-Coder-32B-Instruct",
            "mistralai/Mistral-Small-Instruct-2409",
        ],
    }
    
    ui.info("🤖 Available models by provider:")
    for provider, model_list in models.items():
        ui.info(f"\n📦 {provider.upper()}:")
        for model in model_list:
            ui.info(f"  • {model}")
    
    ui.info("\n💡 Configure with: code-djinn --init")


def handle_clear_cache() -> None:
    """
    Handle cache clearing using new Agno architecture.
    """
    ui = UIManager()
    
    try:
        # Clear config cache
        config_manager = ConfigManager()
        config_manager.clear_cache()
        
        # Clear agent service cache (if any agents were created)
        try:
            config = config_manager.get_agno_config()
            tool_registry = ToolRegistry(config)
            agent_service = AgentService(config, tool_registry)
            agent_service.clear_cache()
        except Exception:
            pass  # Ignore errors during cache clearing
        
        ui.success("✅ All caches cleared successfully")
        
    except Exception as e:
        ui.error(f"❌ Error clearing cache: {str(e)}")
        sys.exit(1)
