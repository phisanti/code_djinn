"""
Configuration Management Commands

Interactive configuration wizard for Code Djinn.
This module is lazy-loaded only when config commands are used.
Heavy dependencies (Rich) are isolated here to avoid runtime overhead.
"""

import configparser
import subprocess
from pathlib import Path
from typing import Optional, Dict, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table

from codedjinn.core.configs import CONFIG_PATH, load_raw_config
from codedjinn.utils.detection import detect_os, detect_shell, get_shell_path

console = Console()

# Available providers and their models
PROVIDERS = {
    "mistralai": {
        "models": [
            "codestral-latest",
            "mistral-small-latest",
            "devstral-medium-latest",
        ],
        "api_key_name": "mistral_api_key",
    },
    "gemini": {
        "models": ["gemini-2.5-flash"],
        "api_key_name": "gemini_api_key",
    },
}


def handle_config(action: str) -> None:
    """
    Route to appropriate config action.

    Args:
        action: One of 'init', 'show', or 'edit'
    """
    actions = {
        "init": init_config,
        "show": show_config,
        "edit": edit_config,
    }

    if action not in actions:
        console.print(f"[red]Unknown action: {action}[/red]")
        console.print("Available actions: init, show, edit")
        raise SystemExit(1)

    actions[action]()


def init_config() -> None:
    """
    Interactive configuration wizard.
    Works on both new and existing configurations.
    """
    console.print(
        Panel.fit(
            "[bold blue]🧞 Code Djinn Configuration[/bold blue]",
            title="Setup",
        )
    )

    # Load existing config if available
    existing = load_raw_config() if CONFIG_PATH.exists() else {}

    # Step 1: OS
    os_family, os_fullname = configure_os(existing.get("os"), existing.get("os_fullname"))

    # Step 2: Shell
    shell, shell_path = configure_shell(existing.get("shell"), existing.get("shell_path"))

    # Step 3: Provider & Model
    provider, model = configure_provider_model(
        existing.get("llm_provider"), existing.get("llm_model")
    )

    # Step 4: API Key
    api_key_name = PROVIDERS[provider]["api_key_name"]
    api_key = configure_api_key(provider, api_key_name, existing.get(api_key_name))

    # Build config dict
    config_data = {
        "os": os_family,
        "os_fullname": os_fullname,
        "shell": shell,
        "shell_path": shell_path,
        "llm_provider": provider,
        "llm_model": model,
        api_key_name: api_key,
    }

    # Save configuration
    save_config_file(config_data)

    console.print(
        Panel.fit(
            f"[green]✅ Configuration saved![/green]\n"
            f"Location: {CONFIG_PATH}",
            title="Success",
        )
    )


def configure_os(
    current_os: Optional[str], current_fullname: Optional[str]
) -> Tuple[str, str]:
    """
    Configure OS settings.

    Args:
        current_os: Existing OS family setting
        current_fullname: Existing OS full name setting

    Returns:
        tuple: (os_family, os_fullname)
    """
    console.print("\n[bold cyan]📍 Operating System[/bold cyan]")

    detected_os, detected_fullname = detect_os()

    if current_os:
        console.print(f"Current: {current_fullname}")
        if not Confirm.ask("Change OS setting?", default=False):
            return current_os, current_fullname

    # New config or user wants to change
    console.print(f"Detected: {detected_fullname}")
    if Confirm.ask("Use detected OS?", default=True):
        return detected_os, detected_fullname

    # Manual input
    os_family = Prompt.ask("Enter OS family (Linux/MacOS/Windows)", default="Linux")
    return os_family, os_family


def configure_shell(
    current_shell: Optional[str], current_path: Optional[str]
) -> Tuple[str, str]:
    """
    Configure shell settings.

    Args:
        current_shell: Existing shell setting
        current_path: Existing shell path setting

    Returns:
        tuple: (shell_name, shell_path)
    """
    console.print("\n[bold cyan]🐚 Shell Environment[/bold cyan]")

    if current_shell:
        display_path = current_path or "path not set"
        console.print(f"Current: {current_shell} ({display_path})")
        if not Confirm.ask("Change shell setting?", default=False):
            return current_shell, current_path or ""

    detected_shell = detect_shell()
    detected_path = get_shell_path(detected_shell)

    console.print(f"Detected: {detected_shell} ({detected_path})")
    if Confirm.ask("Use detected shell?", default=True):
        return detected_shell, detected_path

    # Manual input
    shell = Prompt.ask("Enter shell name (bash/zsh/fish)", default="bash")
    shell_path = get_shell_path(shell)

    if not shell_path:
        console.print(f"[yellow]Warning: Could not find {shell} in PATH[/yellow]")

    return shell, shell_path


def configure_provider_model(
    current_provider: Optional[str], current_model: Optional[str]
) -> Tuple[str, str]:
    """
    Configure LLM provider and model.

    Args:
        current_provider: Existing provider setting
        current_model: Existing model setting

    Returns:
        tuple: (provider, model)
    """
    console.print("\n[bold cyan]🤖 LLM Provider & Model[/bold cyan]")

    if current_provider and current_model:
        console.print(f"Current: {current_provider} / {current_model}")
        if not Confirm.ask("Change provider/model?", default=False):
            return current_provider, current_model

    # Show providers
    console.print("\nAvailable providers:")
    provider_list = list(PROVIDERS.keys())
    for idx, p in enumerate(provider_list, 1):
        models_str = ", ".join(PROVIDERS[p]["models"])
        console.print(f"  {idx}. {p}: {models_str}")

    choice = Prompt.ask(
        "Select provider",
        choices=[str(i) for i in range(1, len(provider_list) + 1)],
        default="1",
    )
    provider = provider_list[int(choice) - 1]

    # Show models for selected provider
    models = PROVIDERS[provider]["models"]
    console.print(f"\nAvailable models for {provider}:")
    for idx, m in enumerate(models, 1):
        # Add helpful hints for models
        hint = ""
        if m == "codestral-latest":
            hint = " [dim](⚡ Fast, recommended)[/dim]"
        elif m == "devstral-medium-latest":
            hint = " [dim](🔬 New, slower, 2x cost)[/dim]"

        console.print(f"  {idx}. {m}{hint}")

    model_choice = Prompt.ask(
        "Select model",
        choices=[str(i) for i in range(1, len(models) + 1)],
        default="1",
    )
    model = models[int(model_choice) - 1]

    return provider, model


def configure_api_key(
    provider: str, api_key_name: str, current_key: Optional[str]
) -> str:
    """
    Configure API key for selected provider.

    Args:
        provider: Provider name for display
        api_key_name: Config key name for the API key
        current_key: Existing API key value

    Returns:
        str: API key
    """
    console.print("\n[bold cyan]🔑 API Key[/bold cyan]")

    if current_key:
        # Mask the key for display
        if len(current_key) > 8:
            masked = f"{current_key[:4]}...{current_key[-4:]}"
        else:
            masked = "***"

        console.print(f"Current {provider} API key: {masked}")
        if not Confirm.ask("Update API key?", default=False):
            return current_key

    new_key = Prompt.ask(f"Enter {provider} API key", password=True)
    return new_key.strip()


def show_config() -> None:
    """Display current configuration in a formatted table."""
    if not CONFIG_PATH.exists():
        console.print(
            "[yellow]No configuration found. Run 'code-djinn config init'[/yellow]"
        )
        return

    config = load_raw_config()

    if not config:
        console.print("[yellow]Configuration file is empty[/yellow]")
        return

    table = Table(title="Code Djinn Configuration", show_header=True)
    table.add_column("Setting", style="cyan", width=25)
    table.add_column("Value", style="green")

    # Display non-sensitive values
    display_keys = ["os", "os_fullname", "shell", "shell_path", "llm_provider", "llm_model"]

    for key in display_keys:
        value = config.get(key, "[dim]not set[/dim]")
        table.add_row(key, str(value))

    # Mask API keys
    for key in config:
        if "api_key" in key or "api_token" in key:
            value = config[key]
            if len(value) > 8:
                masked = f"{value[:4]}...{value[-4:]}"
            else:
                masked = "***"
            table.add_row(key, masked)

    console.print(table)
    console.print(f"\n[dim]Config file: {CONFIG_PATH}[/dim]")


def edit_config() -> None:
    """Open config file in user's default editor."""
    import os

    if not CONFIG_PATH.exists():
        console.print("[yellow]No configuration found. Creating template...[/yellow]")
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            """[DEFAULT]
os = Linux
os_fullname = Linux
shell = bash
shell_path = /bin/bash
llm_provider = mistralai
llm_model = codestral-latest

[API_KEYS]
mistral_api_key = your_key_here
"""
        )

    editor = os.environ.get("EDITOR", "vim")

    try:
        console.print(f"[dim]Opening {CONFIG_PATH} with {editor}...[/dim]")
        subprocess.run([editor, str(CONFIG_PATH)], check=True)
        console.print("[green]✓ Config file updated[/green]")
    except subprocess.CalledProcessError:
        console.print(f"[red]Failed to open editor: {editor}[/red]")
        console.print(f"Edit manually: {CONFIG_PATH}")
    except FileNotFoundError:
        console.print(f"[red]Editor not found: {editor}[/red]")
        console.print(f"Set EDITOR environment variable or edit manually: {CONFIG_PATH}")


def save_config_file(config: Dict[str, str]) -> None:
    """
    Save configuration to file.

    Args:
        config: Configuration dictionary to save
    """
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

    cfg = configparser.ConfigParser()

    # DEFAULT section: non-sensitive settings
    cfg["DEFAULT"] = {
        k: v for k, v in config.items() if not ("api_key" in k or "api_token" in k)
    }

    # API_KEYS section: sensitive credentials
    cfg["API_KEYS"] = {
        k: v for k, v in config.items() if "api_key" in k or "api_token" in k
    }

    with open(CONFIG_PATH, "w") as f:
        cfg.write(f)
