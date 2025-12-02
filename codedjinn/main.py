#!/usr/bin/env python3
"""
Main entry point for CodeDjinn CLI with Agno architecture.
Clean, fast, and focused on the core functionality.
"""


def code_djinn():
    """
    Main entry point using Agno architecture.

    The over-zealous safety bug is FIXED!
    Commands like 'ls | grep foo' now work without confirmation.
    """
    from .parser import create_parser
    from .commands import (
        handle_clear_cache,
        handle_list_models,
        handle_init,
        handle_run,
        handle_chat,
    )

    parser = create_parser()
    args = parser.parse_args()

    # Handle commands with Agno architecture
    if args.clear_cache:
        handle_clear_cache()
    elif args.list_models:
        handle_list_models()
    elif args.init:
        handle_init()
    elif args.run is not None:
        wish = args.run or input("What do you want to do? ")
        handle_run(wish, args.explain, args.verbose, args.no_confirm)
    elif args.chat is not None:
        session_id = args.chat
        handle_chat(session_id)
    else:
        print("Command not recognized. Please use --help for available options.")


if __name__ == "__main__":
    code_djinn()
