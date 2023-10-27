import sys
import os
import argparse
from dotenv import set_key, dotenv_values
from .djinn import djinn
from .utils import get_bolded_text, get_os_info, print_text
from pathlib import Path

def code_djinn():

    """" 
    Parser for the code_djinn CLI    
    """
    
    parser = argparse.ArgumentParser(prog="code_djinn", description="An AI CLI assistant")
    parser.add_argument("-i", "--init", action="store_true", help="Initialize the configuration")
    parser.add_argument("-a", "--ask", metavar="WISH", type=str, nargs="?", help="Get a shell command for the given wish")
    parser.add_argument("-t", "--test", metavar="WISH", type=str, nargs="?", help="Test the promt for the given wish")
    parser.add_argument("-e", "--explain", action="store_true", default=False, help="Also provide an explanation for the command")
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help="Verbose output from AI")
    
    # Parse commands
    args = parser.parse_args()
    if args.init:
        init()
    elif args.test:
        explain = args.explain
        verbose = args.verbose

        if len(args.test) > 1:
            wish = args.test
        else:
            wish = input("What do you want to do? ")
    
        test(wish, explain)
    elif args.ask:
        explain = args.explain
        verbose = args.verbose

        if len(args.ask) > 1:
            wish = args.ask
        else:
            wish = input("What do you want to do? ")

    
        ask(wish, explain, verbose)
    else:
        print("Command not recognised")

def init():

    """"
    Initialize the configuration to get the variables os_family, shell and api_key
    """

    os_family, os_fullname = get_os_info()
    app_dir = os.path.dirname(sys.modules[__name__].__file__)
    env_path = Path(app_dir) / ".env"

    if os_family:
        print_text(f"Detected OS: {os_fullname} \n", color="green")
        answer=input(f'Type yes to confirm or no to input manually: ')
        if answer.lower() == 'yes' or 'y':
            pass
        else:
            os_family = input("What is your OS family? (e.g. Windows, MacOS, Linux): ")

    if os_family in ("Linux", "MacOS"):
        shell_str = os.environ.get("SHELL") or ""
        if "bash" in shell_str:
            shell = "bash"
        elif "zsh" in shell_str:
            shell = "zsh"
        elif "fish" in shell_str:
            shell = "fish"
        else:
            shell = input("What shell are you using? ")
    
    api_key = input("What is your DeepInfra API key? ")

    # Save config
    config = {
        "OS": os_family,
        "OS_FULLNAME": os_fullname,
        "SHELL": shell,
        "DEEPINFRA_API_TOKEN": api_key
    } 

    print("The following configuration will be saved:")
    print_text(config, "red")
    print_text(f"Config file saved at {env_path}", "green")

    for key, value in config.items():
        set_key(env_path, key, value)


def ask(
    wish: str,
    explain: bool = False,
    llm_verbose: bool = False
    ):

    """"
    Ask the djinn for a command, main tool of the CLI
    """
    # Load vars
    app_dir = os.path.dirname(sys.modules[__name__].__file__)
    env_path = Path(app_dir) / ".env"
    config = dotenv_values(env_path)
    
    # Init dinnn
    thedjinn = djinn(os_fullname=config['OS_FULLNAME'],
                     shell=config['SHELL'],
                     api=config['DEEPINFRA_API_TOKEN'])
    
    # Request command
    try:
        command, description = thedjinn.ask(wish, explain, llm_verbose)
    except Exception as e:
        print_text(f"Error: {e}", "red")
        return

    # Deal with response
    if command:
        print("\n")
        print_text(command, "blue")
    if description:
        print_text(f"\nDescription: {description}", "pink")

def test(    wish: str,
    explain: bool = False
    ):
    """"
    Test the promt for a given wish
    """
    config = dotenv_values()
    thedjinn = djinn(os_fullname=config['OS_FULLNAME'],
                     shell=config['SHELL'],
                     api=config['DEEPINFRA_API_TOKEN'])
    try:
        promt = thedjinn.test_prompt(wish, explain)
    except Exception as e:
        print_text(f"Error: {e}", "red")
        return
    if promt:
        print("\n")
        print_text(promt, "blue")

if __name__ == "__main__":
    code_djinn()