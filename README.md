# code_djinn - Your Coding Genie

[![Test](https://github.com/phisanti/code_djinn/actions/workflows/test.yml/badge.svg)](https://github.com/phisanti/code_djinn/actions/workflows/test.yml)
[![Upload Python Package](https://github.com/phisanti/code_djinn/actions/workflows/publish-to-pypi.yml/badge.svg)](https://github.com/phisanti/code_djinn/actions/workflows/publish-to-pypi.yml)
[![PyPI version](https://badge.fury.io/py/code-djinn.svg)](https://pypi.org/project/code-djinn/)
[![Python versions](https://img.shields.io/pypi/pyversions/code-djinn.svg)](https://pypi.org/project/code-djinn/)
[![Development Status](https://img.shields.io/badge/Development%20Status-4%20--%20Beta-yellow.svg)](https://pypi.org/search/?c=Development+Status+%3A%3A+4+-+Beta)

Code Djinn is a lightning-fast CLI assistant that generates shell commands and provides an interactive chat experience. Code Djinn leverages fast and efficient LLM models like QwQ (Qwen), Codestral (Mistral), and Gemini Flash (Google) to provide quick responses to your coding queries. The focus on lightweight models ensures snappy performance and responsiveness, making it a practical tool for your daily coding tasks.

So why spend hours on obscure StackOverflow threads or try to remember arcane CLI commands? Let code_djinn handle the boring stuff so you can focus on building awesome projects! 🧞‍♂️

# Installation

Install Code Djinn from PyPI:

```bash
pip install code-djinn
```

Or from source via:

```bash
pip install git+https://github.com/phisanti/code_djinn.git
```

# Usage

To use Code Djinn, you need to initialize the configuration first. This is a one-time process that will save your preferences and settings. Here’s how you do it:

```bash
code_djinn --init
```

This will prompt you to enter some information, such as:

- Your OS family (e.g. Windows, MacOS, Linux). Code Djinn will detect it automatically.
- Your shell (e.g. bash, zsh, fish). Code Djinn will detect it from your environment variables.
- Your preferred LLM provider (DeepInfra, MistralAI, or Gemini)
- Your API key for the selected provider
- Optional: System preferences for customized command suggestions

## Quick Start

### Generate Commands
```bash
# Basic command generation
code_djinn -a "list files by size"
# Output: ls -lhS

# With explanation
code_djinn -a -e "find large files"
```

### Execute Commands Safely
```bash
# Generate and run with confirmation (default behavior)
code_djinn -r "show disk usage"

# Skip confirmation for safe commands
code_djinn -r --no-confirm "list current directory"
```

### Interactive Chat Mode 🎉 NEW!
```bash
# Start interactive chat session
code_djinn --chat

# Chat with context and command execution
[project-dir]> What files are in this directory?
[project-dir]> Find all Python files larger than 1MB
[project-dir]> exit
```

## Available Commands

```bash
# Generate commands
code_djinn -a "your request"           # Fast command generation
code_djinn -a -e "your request"        # With explanation
code_djinn -a -v "your request"        # Verbose LLM output

# Execute commands safely  
code_djinn -r "your request"           # Generate and run with confirmation
code_djinn -r --no-confirm "request"   # Skip confirmation for safe commands

# Interactive chat mode
code_djinn --chat                      # Start interactive chat session

# Utilities
code_djinn --init                      # Setup configuration
code_djinn --list-models              # Show available LLM models
code_djinn --clear-cache              # Clear performance cache
```

## Interactive Chat Mode Features

The new chat mode provides a conversational interface with advanced capabilities:

- **Context-aware conversations**: Remembers your previous interactions
- **Directory awareness**: Shows current directory in prompt
- **Mixed responses**: Can provide both answers and executable commands
- **Smart command detection**: Automatically identifies when you need a command vs. conversation
- **Safe execution**: Commands require confirmation with clear prompts
- **Session management**: Type `clear` to reset context, `exit` to quit

```bash
# Example chat session
code_djinn --chat

🧞 Code Djinn Chat Mode 
Type 'exit' to quit, 'clear' to clear context

[my-project]> How are you today?
I'm doing great! Ready to help with your command-line tasks.

[my-project]> Show me all Python files
find . -name "*.py" -type f

Execute? (enter to confirm or type n/no to cancel): 
✓ Done

[my-project]> What did that command do?
That command searched for all Python files (.py extension) in the current directory and subdirectories.
```

## Supported Providers & Models

- **DeepInfra**: QwQ-32B, Qwen2.5-Coder-32B, Mistral-Small-24B
- **MistralAI**: codestral-latest, mistral-small-latest, devstral-medium-latest  
- **Google**: gemini-2.0-flash

## Help

Use the `--help` flag to see all available options:

```bash
❯ code_djinn --help 
usage: code_djinn [-h] [-i] [-t [WISH]] [-e] [-v] [--list-models] [-r [WISH]]
                  [--no-confirm] [--clear-cache] [--chat [SESSION_ID]]

An AI CLI assistant

options:
  -h, --help            show this help message and exit
  -i, --init            Initialize the configuration
  -e, --explain         Also provide an explanation for the command
  -v, --verbose         Verbose output from AI
  --list-models         List available models for all providers
  -r [WISH], --run [WISH]
                        Generate and run a shell command (with confirmation by default)
  --no-confirm          Skip confirmation for safe commands when using --run
  --clear-cache         Clear LLM client cache for troubleshooting
  --chat [SESSION_ID]   Start interactive chat mode (optionally resume session)
```

## Troubleshooting

If you encounter issues:

1. **Clear the cache**: `code_djinn --clear-cache`
2. **Reinitialize configuration**: `code_djinn --init`
3. **Check your API key**: Ensure it's valid and has proper permissions

For more help, [open an issue](https://github.com/phisanti/code_djinn/issues) on GitHub!

# Bonus

What's djinn (“جن”)?
In Arabic mythology, a Djinn (also spelled as Jinn or Genie) is a supernatural creature that is made from smokeless and scorching fire. They are often depicted as powerful and free-willed beings who can be either benevolent or malevolent. Djinns are believed to have the ability to shape-shift and can take on various forms, such as humans or animals. They are also known for their exceptional strength and their ability to travel great distances at extreme speeds. Despite their supernatural abilities, Djinns, like humans, are subject to judgment and will either be condemned to hell or rewarded with heaven in the afterlife.
