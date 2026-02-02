"""Main CLI entry point - clean subcommand architecture with daemon support."""

import sys
from pathlib import Path
from typing import Optional, Tuple
import typer

from codedjinn.core.configs import load_raw_config, get_model_config
from codedjinn.core.policy import check_and_confirm
from codedjinn.core.session import Session
from codedjinn.providers.mistral import MistralAgent
from codedjinn.tools.exec_shell import execute_command
from codedjinn.tools.output_trimmer import trim_output

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Code Djinn - Your AI shell command assistant.",
)


# ============================================================================
# Daemon Mode Detection
# ============================================================================

def _should_use_daemon() -> bool:
    """Check if we should use daemon mode."""
    from codedjinn.daemon.client import is_daemon_enabled
    return is_daemon_enabled()


def _get_daemon_client():
    """Get daemon client (lazy import for performance)."""
    from codedjinn.daemon.client import DaemonClient
    return DaemonClient()


# ============================================================================
# Shared Setup - Performance critical: called on every invocation
# ============================================================================

def _setup_agent_and_context() -> Tuple:
    """
    Load config and create agent. Exits on error.

    Returns: (agent, context_dict)

    Performance: Config loading is cached, agent creation is fast.
    Future agents: This is the single source of truth for agent setup.
    """
    try:
        raw_config = load_raw_config()
        model_config = get_model_config(raw_config)
    except Exception as e:
        typer.echo(f"Error loading configuration: {e}", err=True)
        typer.echo("Run 'code-djinn settings init' to set up configuration", err=True)
        raise typer.Exit(1)

    # Warn if not using mistralai (but continue - user may be testing)
    if model_config.provider != 'mistralai':
        typer.echo(
            f"WARNING: Currently only supports 'mistralai' provider (got: {model_config.provider})",
            err=True
        )

    try:
        agent = MistralAgent(api_key=model_config.api_key, model=model_config.model)
    except Exception as e:
        typer.echo(f"Error initializing agent: {e}", err=True)
        raise typer.Exit(1)

    # Build execution context - minimal dict for performance
    context = {
        'cwd': Path.cwd(),
        'os_name': raw_config.get('os', 'Linux'),
        'shell': raw_config.get('shell', 'bash')
    }

    return agent, context


def _get_session_context(no_context: bool, verbose: bool) -> Tuple:
    """
    Load session and previous context.

    Returns: (session, previous_context_dict_or_none)

    Performance: Session loading is I/O bound, unavoidable.
    Future agents: --no-context flag clears session, otherwise loads previous command.
    """
    session = Session(session_name="default")

    if no_context:
        session.clear()
        return session, None

    previous_context = session.get_context_for_prompt()
    if previous_context and verbose:
        typer.echo(f"[Using context from: {previous_context['command']}]")

    return session, previous_context


# ============================================================================
# Commands - Each command is linear: setup → execute → handle result
# ============================================================================

@app.command()
def ask(
    query: str = typer.Argument(..., help="Question about previous command output"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
    no_context: bool = typer.Option(False, "--no-context", help="Ignore previous context"),
    steps: int = typer.Option(0, "--steps", min=0, max=10, help="Reasoning steps (0-10, default 0=fast, use --steps 3 for multi-step)"),
    no_daemon: bool = typer.Option(False, "--no-daemon", help="Force direct mode (no daemon)"),
) -> None:
    """
    Ask a question about the previous command output (no execution).

    Single-shot mode (default):
        code-djinn ask "what files were modified?"

    Multi-step reasoning (new):
        code-djinn ask "explain the error" --steps 3 -v

    Can read files from disk to provide better context (when using steps > 0).
    """
    # Try daemon mode first (faster if available)
    if _should_use_daemon() and not no_daemon:
        client = _get_daemon_client()
        if client.ensure_daemon_running():
            success, result = client.ask(
                query=query,
                cwd=str(Path.cwd()),
                session_name="default",
                no_context=no_context,
                steps=steps,
            )
            if success:
                # Display tool calls for accountability (always show)
                tool_calls = result.get("tool_calls", [])
                if tool_calls:
                    typer.echo("\n[Tools used]")
                    for tool_call in tool_calls:
                        tool = tool_call.get("tool", "unknown")
                        context = tool_call.get("context", "")
                        if tool == "read_file":
                            path = tool_call.get("path", "")
                            output = tool_call.get("output", "")
                            typer.echo(f"  📄 read_file: {path}")
                            if context:
                                typer.echo(f"     Reason: {context}")
                            typer.echo(f"     Output: {output}")
                        elif tool == "execute_observe_command":
                            command = tool_call.get("command", "")
                            output = tool_call.get("output", "")
                            typer.echo(f"  🔍 execute_observe_command: {command}")
                            if context:
                                typer.echo(f"     Reason: {context}")
                            typer.echo(f"     Output: {output}")
                    typer.echo()
                
                # Display the answer
                typer.echo(result.get("response", ""))
                return
            # Fall through to direct mode on error

    # Direct mode (fallback)
    agent, context = _setup_agent_and_context()
    session, previous_context = _get_session_context(no_context, verbose)

    # Load conversation history for multi-step reasoning (Phase 4)
    conversation_history = None
    if not no_context and session and steps > 0:
        conversation_history = session.get_conversation_history()
        if conversation_history and verbose:
            typer.echo(f"[Using conversation history: {len(conversation_history)} previous command(s)]")

    try:
        # Route based on steps
        if steps > 0:
            # Multi-step reasoning mode
            response = agent.analyze_with_steps(
                query,
                context,
                max_steps=steps,
                previous_context=previous_context,
                conversation_history=conversation_history  # Phase 4: Conversation history
            )
            typer.echo(response)
        else:
            # Simple single-shot mode with tool tracking
            result = agent.analyze(
                query,
                context,
                previous_context=previous_context,
            )
            
            # Display tool calls for accountability (always show)
            tool_calls = result.get("tool_calls", [])
            if tool_calls:
                typer.echo("\n[Tools used]")
                for tool_call in tool_calls:
                    tool = tool_call.get("tool", "unknown")
                    context_str = tool_call.get("context", "")
                    if tool == "read_file":
                        path = tool_call.get("path", "")
                        output = tool_call.get("output", "")
                        typer.echo(f"  📄 read_file: {path}")
                        if context_str:
                            typer.echo(f"     Reason: {context_str}")
                        typer.echo(f"     Output: {output}")
                    elif tool == "execute_observe_command":
                        command = tool_call.get("command", "")
                        output = tool_call.get("output", "")
                        typer.echo(f"  🔍 execute_observe_command: {command}")
                        if context_str:
                            typer.echo(f"     Reason: {context_str}")
                        typer.echo(f"     Output: {output}")
                typer.echo()
            
            # Display the answer
            typer.echo(result.get("answer", ""))
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def run(
    query: str = typer.Argument(..., help="Prompt to generate and execute command"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
    silent: bool = typer.Option(False, "--silent", help="Suppress echoing the generated command"),
    no_confirm: bool = typer.Option(False, "--no-confirm", help="Skip safety confirmation"),
    no_context: bool = typer.Option(False, "--no-context", help="Ignore previous context"),
    no_daemon: bool = typer.Option(False, "--no-daemon", help="Force direct mode (no daemon)"),
    steps: int = typer.Option(0, "--steps", min=0, help="Tool call budget (currently only 0 supported)"),
    add_context: Optional[str] = typer.Option(None, "--add-context", help="Add files to context (comma-separated)"),
) -> None:
    """
    Generate and execute a shell command.

    Example: code-djinn run "find all python files modified today"

    Performance: Single-shot LLM call, command execution streams output in real-time.
    """
    # Validate steps parameter (Phase 1: single-shot only)
    if steps != 0:
        typer.echo("WARNING: Only --steps 0 supported. Using single-shot mode.", err=True)

    # Handle --add-context flag (add files before running)
    if add_context:
        from codedjinn.context.sources.files import get_file_context_manager, parse_duration
        files = [f.strip() for f in add_context.split(",")]
        manager = get_file_context_manager()
        result = manager.add_files(files, parse_duration("10m"))
        if result['added'] and verbose:
            typer.echo(f"[Added {len(result['added'])} file(s) to context]")
        if result['errors']:
            for err in result['errors']:
                typer.echo(f"[Context error: {err}]", err=True)

    cwd = Path.cwd()
    command = None

    # Try daemon mode first (faster if available)
    if _should_use_daemon() and not no_daemon:
        client = _get_daemon_client()
        if client.ensure_daemon_running():
            success, result = client.run(
                query=query,
                cwd=str(cwd),
                session_name="default",
                no_context=no_context,
                verbose=verbose,
            )
            if success:
                command = result.get("command")
                # Use daemon for session later
    
    # Fallback to direct mode if daemon didn't work
    if command is None:
        agent, context = _setup_agent_and_context()
        session, previous_context = _get_session_context(no_context, verbose)

        try:
            command = agent.generate_command(query, context, previous_context=previous_context)
        except Exception as e:
            typer.echo(f"Error generating command: {e}", err=True)
            raise typer.Exit(1)

    # Echo command unless configured to stay silent
    if not silent:
        typer.echo(f"→ {command}\n")

    # Safety check - user confirmation for dangerous commands
    if not no_confirm and not check_and_confirm(command):
        typer.echo("Cancelled by user.", err=True)
        raise typer.Exit(1)

    # Execute and capture output (performance: streams to terminal in real-time)
    exit_code, output = execute_command(command, cwd=cwd)

    # Save to session for next command
    if not no_context:
        trimmed_output = trim_output(output, max_lines=30, max_chars=2000)
        
        # Try to save via daemon if available
        if _should_use_daemon() and not no_daemon:
            client = _get_daemon_client()
            client.save_session(
                session_name="default",
                command=command,
                output=trimmed_output,
                exit_code=exit_code,
            )
        else:
            # Direct mode: save to disk
            session = Session(session_name="default")
            session.save(command, trimmed_output, exit_code)

    # Exit with command's actual exit code (preserves shell semantics)
    raise typer.Exit(exit_code)


@app.command()
def settings(
    action: str = typer.Argument(..., help="Action: init, show, or edit"),
) -> None:
    """
    Manage Code Djinn configuration.

    Actions:
        init - Interactive configuration wizard
        show - Display current configuration
        edit - Open config file in $EDITOR

    Performance: Lazy import config_commands to avoid startup overhead.
    """
    from codedjinn.ui.config_commands import handle_config
    handle_config(action)


@app.command()
def daemon(
    action: str = typer.Argument(..., help="Action: start, stop, status, restart"),
) -> None:
    """
    Manage the Code Djinn daemon.

    Actions:
        start   - Start daemon in background
        stop    - Stop running daemon
        status  - Show daemon status
        restart - Restart daemon
    """
    from codedjinn.daemon.client import DaemonClient, get_pid_path
    
    client = DaemonClient()
    
    if action == "start":
        if client.is_daemon_running():
            typer.echo("Daemon is already running")
        else:
            typer.echo("Starting daemon...")
            if client.ensure_daemon_running(auto_start=True):
                typer.echo("Daemon started")
            else:
                typer.echo("Failed to start daemon", err=True)
                raise typer.Exit(1)
    
    elif action == "stop":
        if not client.is_daemon_running():
            typer.echo("Daemon is not running")
        else:
            typer.echo("Stopping daemon...")
            if client.shutdown():
                typer.echo("Daemon stopped")
            else:
                typer.echo("Failed to stop daemon", err=True)
                raise typer.Exit(1)
    
    elif action == "status":
        stats = client.health()
        if stats:
            typer.echo("Daemon status: running")
            typer.echo(f"  Uptime: {stats.get('uptime_seconds', 0):.0f}s")
            typer.echo(f"  Cached contexts: {stats.get('cached_contexts', 0)}")
            typer.echo(f"  Active sessions: {stats.get('active_sessions', 0)}")
        else:
            typer.echo("Daemon status: not running")
    
    elif action == "restart":
        if client.is_daemon_running():
            typer.echo("Stopping daemon...")
            client.shutdown()
            import time
            time.sleep(0.5)
        typer.echo("Starting daemon...")
        if client.ensure_daemon_running(auto_start=True):
            typer.echo("Daemon restarted")
        else:
            typer.echo("Failed to restart daemon", err=True)
            raise typer.Exit(1)
    
    else:
        typer.echo(f"Unknown action: {action}", err=True)
        typer.echo("Valid actions: start, stop, status, restart", err=True)
        raise typer.Exit(1)


@app.command()
def context(
    action: str = typer.Argument(..., help="Action: add, list, drop, clear"),
    files: Optional[list[str]] = typer.Argument(None, help="Files for add/drop actions"),
    duration: str = typer.Option("10m", "--duration", "-d", help="Duration for add (e.g., 10m, 1h, 1d)"),
) -> None:
    """
    Manage file context for Code Djinn.

    Actions:
        add   - Add files to context
        list  - Show files in context
        drop  - Remove files from context
        clear - Clear all file context

    Examples:
        code-djinn context add src/main.py --duration 30m
        code-djinn context list
        code-djinn context drop src/main.py
        code-djinn context clear

    Performance: Lazy import context_commands to avoid startup overhead.
    """
    from codedjinn.ui.context_commands import handle_context
    handle_context(action, files=files, duration=duration)


def run() -> None:
    """Entry point for console script mapping."""
    app()


if __name__ == "__main__":
    run()
