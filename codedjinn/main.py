#!/usr/bin/env python3
"""
Clean main entry point for CodeDjinn CLI.
Command handlers extracted to commands module for better architecture and easier testing.
"""


def code_djinn():
    """
    Main entry point with delayed imports and optimized command handling.
    """
    from .parser import create_parser
    from .commands import (
        handle_clear_cache, handle_list_models, handle_init,
        handle_test, handle_run, handle_chat
    )
    
    parser = create_parser()
    args = parser.parse_args()
    
    # Handle commands in order of likelihood and performance impact
    if args.clear_cache:
        handle_clear_cache()
    elif args.list_models:
        handle_list_models()
    elif args.init:
        handle_init()
    elif args.test is not None:
        wish = args.test or input("What do you want to do? ")
        handle_test(wish, args.explain)
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