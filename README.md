# code_djinn - Your Coding Genie

[![Test](https://github.com/phisanti/code_djinn/actions/workflows/test.yml/badge.svg)](https://github.com/phisanti/code_djinn/actions/workflows/test.yml)
[![Upload Python Package](https://github.com/phisanti/code_djinn/actions/workflows/publish-to-pypi.yml/badge.svg)](https://github.com/phisanti/code_djinn/actions/workflows/publish-to-pypi.yml)
[![PyPI version](https://badge.fury.io/py/code-djinn.svg)](https://pypi.org/project/code-djinn/)
[![Python versions](https://img.shields.io/pypi/pyversions/code-djinn.svg)](https://pypi.org/project/code-djinn/)
[![Development Status](https://img.shields.io/badge/Development%20Status-4%20--%20Beta-yellow.svg)](https://pypi.org/search/?c=Development+Status+%3A%3A+4+-+Beta)

Code Djinn is a lightning-fast CLI assistant that generates and executes shell commands using AI. Powered by Mistral AI, Code Djinn translates natural language requests into shell commands with safety checks and automatic context awareness. The tool remembers your previous commands, allowing natural follow-up queries without repetition.

Stop searching StackOverflow or memorizing arcane CLI syntax. Let Code Djinn handle the boring stuff so you can focus on building awesome projects! 🧞‍♂️

# Installation

Install Code Djinn from PyPI:

```bash
# Using pip
pip install code-djinn

# Using uv (faster)
uv pip install code-djinn

# Using uv tool (isolated environment, recommended)
uv tool install code-djinn
```

Or from source:

```bash
git clone https://github.com/phisanti/code_djinn.git
cd code_djinn
uv pip install -e .
```

# Usage

First-time setup (initialize configuration):

```bash
code-djinn settings init
```

This interactive wizard will prompt you for:

- Your OS family (auto-detected: Windows, MacOS, Linux)
- Your shell (auto-detected: bash, zsh, fish, etc.)
- Your preferred LLM provider (currently supports **MistralAI**)
- Your Mistral API key ([get one here](https://console.mistral.ai/))
- Model selection (mistral-small-latest, codestral-latest, etc.)

## Quick Start

### Generate and Execute Commands
```bash
# Basic command execution with safety confirmation
code-djinn run "list files by size"
# → Generates: ls -lhS
# → Asks for confirmation
# → Executes and shows output

# Show command before execution (verbose mode)
code-djinn run "find large files" -v

# Skip confirmation for safe commands
code-djinn run "show current date" --no-confirm
```

### Ask Questions and Observe Your System
```bash
# Ask about the previous command's output
code-djinn run "git log --oneline -n 10"
code-djinn ask "what was the last commit about?"

# Ask about running processes (no prior command needed)
code-djinn ask "what is the hq process doing?"
code-djinn ask "which processes are using the most memory?"
code-djinn ask "what network connections does process 1234 have?"

# Ask about code or files
code-djinn ask "where is the database connection configured?"
code-djinn ask "explain the error in the last output"

# Start fresh (ignore previous context)
code-djinn run "list python files" --no-context
```

Ask mode can read files, run safe observation commands (`ps`, `pgrep`, `lsof`, `netstat`, `git log`, etc.) and search code — without executing any destructive commands.

### Daemon Management

Code Djinn runs a background daemon that keeps the Mistral client warm, reducing per-request overhead from ~900ms to ~5ms.

```bash
code-djinn daemon status   # Check if daemon is running
code-djinn daemon start    # Start daemon manually
code-djinn daemon stop     # Stop daemon
code-djinn daemon restart  # Restart daemon
```

The daemon starts automatically on first use and shuts down after 1 hour idle. Set `CODEDJINN_NO_DAEMON=1` to force direct mode.

### File Context Management

Pin files into ask/run context so the agent can reference them without you quoting paths:

```bash
code-djinn context add src/main.py           # Add file (default 10m duration)
code-djinn context add src/main.py -d 1h     # Add with 1-hour expiry
code-djinn context list                       # Show active context files
code-djinn context drop src/main.py          # Remove a file
code-djinn context clear                      # Clear all file context
```

### Configuration Management
```bash
# View current configuration
code-djinn settings show

# Reconfigure settings
code-djinn settings init

# Edit config file directly
code-djinn settings edit
```

## Available Commands

```bash
# Generate and execute commands
code-djinn run "your request"              # Generate and execute with confirmation
code-djinn run "your request" -v           # Show command before execution
code-djinn run "your request" --no-confirm # Skip safety confirmation
code-djinn run "your request" --no-context # Ignore previous command context

# Ask questions / observe system
code-djinn ask "your question"             # Analyze output, read files, observe processes
code-djinn ask "your question" -v          # Verbose output
code-djinn ask "your question" --no-context # Ignore previous context

# Daemon management
code-djinn daemon status                   # Check if daemon is running
code-djinn daemon start                    # Start daemon
code-djinn daemon stop                     # Stop daemon
code-djinn daemon restart                  # Restart daemon

# File context
code-djinn context add <file> [-d 10m]    # Pin a file into context
code-djinn context list                    # Show active context files
code-djinn context drop <file>            # Remove a file from context
code-djinn context clear                   # Clear all file context

# Configuration management
code-djinn settings init                   # Interactive configuration wizard
code-djinn settings show                   # Display current configuration
code-djinn settings edit                   # Open config file in $EDITOR
```

## Key Features

- **Context Awareness**: Automatically remembers previous commands and their output
- **Process & System Observation**: Ask mode can inspect running processes (`pgrep`, `lsof`, `ps`, `netstat`) without executing destructive commands
- **Safety First**: Analyzes commands for potential risks and requires confirmation
- **Real-time Streaming**: Command output streams directly to your terminal
- **Background Daemon**: Keeps the Mistral client warm for ~5ms response overhead (vs ~900ms cold start)
- **File Context Pinning**: Attach files to the session so the agent references them automatically
- **Smart Parsing**: Handles both XML-structured and plain text LLM responses
- **Session Management**: Persistent context across CLI invocations

## Supported Providers & Models

**Currently Active:**
- **MistralAI** (native implementation, no langchain dependency)
  - `mistral-small-latest` - Fast, general-purpose model
  - `codestral-latest` - Optimized for code generation
  - `devstral-medium-latest` - Balanced performance/quality

**Legacy (may be deprecated):**
- DeepInfra (via langchain) - QwQ-32B, Qwen2.5-Coder-32B
- Google Gemini (via langchain) - gemini-2.0-flash

## Help

Use the `--help` flag to see all available options:

```bash
❯ code-djinn --help

 Usage: code-djinn [OPTIONS] COMMAND [ARGS]...

 Code Djinn - Your AI shell command assistant.

╭─ Options ────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                              │
╰──────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────╮
│ ask       Ask a question about the previous command output (no execution)│
│ run       Generate and execute a shell command.                          │
│ settings  Manage Code Djinn configuration.                               │
│ daemon    Manage the Code Djinn daemon.                                  │
│ context   Manage file context for Code Djinn.                            │
╰──────────────────────────────────────────────────────────────────────────╯

# Get help for specific commands
❯ code-djinn run --help
❯ code-djinn ask --help
❯ code-djinn daemon --help
❯ code-djinn context --help
❯ code-djinn settings --help
```

## Troubleshooting

If you encounter issues:

1. **Check configuration**: `code-djinn settings show`
2. **Reinitialize configuration**: `code-djinn settings init`
3. **Edit config manually**: `code-djinn settings edit`
   - Config location: `~/.config/codedjinn/config.cfg`
4. **Verify API key**: Ensure your Mistral API key is valid
5. **Clear session context**: `code-djinn run "your command" --no-context`
6. **Restart the daemon**: `code-djinn daemon restart`
7. **Disable daemon** (force direct mode): `CODEDJINN_NO_DAEMON=1 code-djinn run "..."`
8. **Check Python cache**:
   ```bash
   find ~/.local/share/codedjinn -type f -name "*.json"
   rm -rf ~/.local/share/codedjinn/sessions/  # Clear all sessions
   ```

For more help, [open an issue](https://github.com/phisanti/code_djinn/issues) on GitHub!

# Bonus

What's djinn (“جن”)?
In Arabic mythology, a Djinn (also spelled as Jinn or Genie) is a supernatural creature that is made from smokeless and scorching fire. They are often depicted as powerful and free-willed beings who can be either benevolent or malevolent. Djinns are believed to have the ability to shape-shift and can take on various forms, such as humans or animals. They are also known for their exceptional strength and their ability to travel great distances at extreme speeds. Despite their supernatural abilities, Djinns, like humans, are subject to judgment and will either be condemned to hell or rewarded with heaven in the afterlife.
