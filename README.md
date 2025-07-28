# code_djinn - Your Coding Genie

[![Test](https://github.com/phisanti/code_djinn/actions/workflows/test.yml/badge.svg)](https://github.com/phisanti/code_djinn/actions/workflows/test.yml)
[![Upload Python Package](https://github.com/phisanti/code_djinn/actions/workflows/publish-to-pypi.yml/badge.svg)](https://github.com/phisanti/code_djinn/actions/workflows/publish-to-pypi.yml)
[![PyPI version](https://badge.fury.io/py/code-djinn.svg)](https://pypi.org/project/code-djinn/)
[![Python versions](https://img.shields.io/pypi/pyversions/code-djinn.svg)](https://pypi.org/project/code-djinn/)
[![Development Status](https://img.shields.io/badge/Development%20Status-4%20--%20Beta-yellow.svg)](https://pypi.org/search/?c=Development+Status+%3A%3A+4+-+Beta)

Code Djinn is a lightning-fast CLI assistant that generates shell. Code Djinn leverages fast and efficient LLM models like QwQ (Qween), Codestral (Mistral), and Gemini flash (Google) to provide quick responses to your coding queries. The focus on lightweight models ensures snappy performance and responsiveness, making it a practical tool for your daily coding tasks.

So why spend hours on obscure StackOverflow threads or try to remember arcane CLI commands? Let code_djinn handle the boring stuff so you can focus on building awesome projects! 🧞‍♂️

# Installation

Installing Code Djinn from source via:

```bash
pip install git+https://github.com/phisanti/code_djinn.git

```

# Usage

To use Code Djinn, you need to initialize the configuration first. This is a one-time process that will save your preferences and settings. Here’s how you do it:

```
code-djinn --init
```

This will prompt you to enter some information, such as:

- Your OS family (e.g. Windows, MacOS, Linux). Code Djinn will try to detect it automatically, but you can also input it manually if it's wrong.
- Your shell (e.g. bash, zsh, fish). Code Djinn will try to guess it from your environment variables, but you can also input it manually if it's wrong.
- Your DeepInfra API key. This is required to access the AI engine that powers Code Djinn. Also, currently, the only model implemented is mistra7B, so, you have to activate that model.

Summon code-djinn by describing what you want to do:

Generate commands instantly:

```bash
# Basic command generation
code-djinn -a "list files by size"
# Output: ls -lhS

# With explanation
code-djinn -a -e "find large files"

# Execute with confirmation
code-djinn -x "show disk usage"
```

## Available Commands

```bash
# Generate commands
code-djinn -a "your request"           # Fast command generation
code-djinn -a -e "your request"        # With explanation
code-djinn -a -v "your request"        # Verbose LLM output

# Execute commands safely  
code-djinn -x "your request"           # Generate and execute with confirmation

# Utilities
code-djinn --init                      # Setup configuration
code-djinn --list-models              # Show available LLM models
code-djinn -t "your request"          # Test prompt generation
code-djinn --clear-cache              # Clear performance cache
```

## Supported Providers & Models

- **DeepInfra**: QwQ-32B, Qwen2.5-Coder-32B, Mistral-Small-24B
- **MistralAI**: codestral-2501, mistral-small-2503
- **Google**: gemini-2.0-flash

If you have any doubt, please open an issue!

## Help

Currently, this tool is quite simple and all documentation can be found through the `--help` flag. Here is a quick summary:

```bash
❯ code-djinn --help                                                                                                                                                                                                                                                                                                                                                                                                                                                                             (codedjinn_dev) 
usage: code_djinn [-h] [-i] [-a [WISH]] [-t [WISH]] [-e] [-v] [--list-models] [-x [WISH]] [--clear-cache]

An AI CLI assistant

options:
  -h, --help            show this help message and exit
  -i, --init            Initialize the configuration
  -a [WISH], --ask [WISH]
                        Get a shell command for the given wish
  -t [WISH], --test [WISH]
                        Test the prompt for the given wish
  -e, --explain         Also provide an explanation for the command
  -v, --verbose         Verbose output from AI
  --list-models         List available models for all providers
  -x [WISH], --execute [WISH]
                        Generate and execute a shell command for the given wish
  --clear-cache         Clear LLM client cache for troubleshooting
```
# Bonus

What's djinn (“جن”)?
In Arabic mythology, a Djinn (also spelled as Jinn or Genie) is a supernatural creature that is made from smokeless and scorching fire. They are often depicted as powerful and free-willed beings who can be either benevolent or malevolent. Djinns are believed to have the ability to shape-shift and can take on various forms, such as humans or animals. They are also known for their exceptional strength and their ability to travel great distances at extreme speeds. Despite their supernatural abilities, Djinns, like humans, are subject to judgment and will either be condemned to hell or rewarded with heaven in the afterlife.
