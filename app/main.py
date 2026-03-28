import sys

from app.cli.app import cli
from app.cli.commands_chat import chat_command


def run() -> None:
    cli()


def run_sanky() -> None:
    """Entry point for 'sanky' command - launches chat by default."""
    if len(sys.argv) == 1:
        # No arguments: launch chat mode
        chat_command()
    else:
        # With arguments: use normal CLI
        cli()


if __name__ == "__main__":
    run()

