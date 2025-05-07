#!/usr/bin/env python3
"""Entry point for linkhut-cli.

This module serves as the main entry point for the LinkHut CLI application.
It handles environment variable checking before launching the application.
"""

from .cli import app, check_env_variables

def main():
    """Run the CLI application.
    
    This function initializes and runs the LinkHut CLI application.
    It first verifies that all required environment variables are set,
    then launches the Typer CLI app.
    
    Returns:
        None
    """
    check_env_variables()  # Check environment variables before running commands
    app()

if __name__ == "__main__":
    main()