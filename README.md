# code_djinn - Your Coding Genie
Code Djinn is a command-line tool that can help you solve simple code questions. It’s like having a personal coding assistant who understands that “Hello, World!” is more than just a greeting, and that Python has nothing to do with snakes!

So why spend hours on obscure StackOverflow threads or try to remember arcane CLI commands? Let code_djinn handle the boring stuff so you can focus on building awesome projects! 🧞‍♂️

# Installation

Installing Code Djinn is as easy as pie. And not one of those complicated pies, like shepherd's pie. More like an apple pie. Here's how you do it:

```bash
pip install git+https://github.com/phisanti/code_djinn.git

```
If you see any errors during the installation, it’s probably because the stars are not correctly aligned or you’re not holding your laptop at the right angle. Try turning it off and on again.

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

```
$ code-djinn "How to list files sorted by size"
```
code_djinn will think for a few seconds and respond with:

```
ls -lS
```
However, as you know AI models can be a bit temperamental, so you might get something random. Please use code_djinn responsibly!
For more info, just use the help command:

```
$ code-djinn --help
usage: code_djinn [-h] [-i] [-a [WISH]] [-t [WISH]] [-e] [-v]

An AI CLI assistant

options:
  -h, --help            show this help message and exit
  -i, --init            Initialize the configuration
  -a [WISH], --ask [WISH]
                        Get a shell command for the given wish
  -t [WISH], --test [WISH]
                        Test the promt for the given wish
  -e, --explain         Also provide an explanation for the command
  -v, --verbose         Verbose output from AI

  ```

If you have any doubt, please open an issue!

# Bonus

What's djinn (“جن”)?
In Arabic mythology, a Djinn (also spelled as Jinn or Genie) is a supernatural creature that is made from smokeless and scorching fire. They are often depicted as powerful and free-willed beings who can be either benevolent or malevolent. Djinns are believed to have the ability to shape-shift and can take on various forms, such as humans or animals. They are also known for their exceptional strength and their ability to travel great distances at extreme speeds. Despite their supernatural abilities, Djinns, like humans, are subject to judgment and will either be condemned to hell or rewarded with heaven in the afterlife.