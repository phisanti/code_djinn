# code_djinn - Your Coding Genie

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
code_djinn --init
```

This will prompt you to enter some information, such as:

- Your OS family (e.g. Windows, MacOS, Linux). Code Djinn will try to detect it automatically, but you can also input it manually if it’s wrong.
- Your shell (e.g. bash, zsh, fish). Code Djinn will try to guess it from your environment variables, but you can also input it manually if it’s wrong.
- Your DeepInfra API key. This is required to access the AI engine that powers Code Djinn. Also, currently, the only model implemented is mistra7B, so, you have to activate that model.

Summon code_djinn by describing what you want to do:

Generate commands instantly:

```bash
# Basic command generation
code_djinn -a "list files by size"
# Output: ls -lhS

# With explanation
code_djinn -a -e "find large files"

# Execute with confirmation
code_djinn -x "show disk usage"
```

## Available Commands

```bash
# Generate commands
code_djinn -a "your request"           # Fast command generation
code_djinn -a -e "your request"        # With explanation
code_djinn -a -v "your request"        # Verbose LLM output

# Execute commands safely  
code_djinn -x "your request"           # Generate and execute with confirmation

# Utilities
code_djinn --init                      # Setup configuration
code_djinn --list-models              # Show available LLM models
code_djinn -t "your request"          # Test prompt generation
code_djinn --clear-cache              # Clear performance cache
```

## Supported Providers & Models

- **DeepInfra**: QwQ-32B, Qwen2.5-Coder-32B, Mistral-Small-24B
- **MistralAI**: codestral-2501, mistral-small-2503
- **Google**: gemini-2.0-flash

If you have any doubt, please open an issue!

# Bonus

What's djinn (“جن”)?
In Arabic mythology, a Djinn (also spelled as Jinn or Genie) is a supernatural creature that is made from smokeless and scorching fire. They are often depicted as powerful and free-willed beings who can be either benevolent or malevolent. Djinns are believed to have the ability to shape-shift and can take on various forms, such as humans or animals. They are also known for their exceptional strength and their ability to travel great distances at extreme speeds. Despite their supernatural abilities, Djinns, like humans, are subject to judgment and will either be condemned to hell or rewarded with heaven in the afterlife.
