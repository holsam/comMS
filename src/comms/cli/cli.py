'''
comMS ENTRYPOINT
'''

# -- Import external dependencies
import logging, typer
from typing import Annotated

# -- Import internal utility functions
# TODO

# -- Import comMS commands
# TODO - format:
# from comms.cli.command import commsCommand

# -- Print startup splash
# TODO: initComms()

# -- Initialise root Typer class
comms = typer.Typer(
    # Set markup mode so can use rich formatting
    rich_markup_mode="rich",
    # Disable the Typer add completion hints to help page
    add_completion=False,
    # Set that running comms command only provides help page
    no_args_is_help=True,
)


# -- Register (sub)Typer classes for each command
# TODO - format:
#  comms.add_typer(Typer) <- standard
#  comms.add_typer(Typer, name='command', help='help text', rich_help_panel='help panel') <- for commands with subcommands


# ====================
# Top-level callback: --verbose / --debug flags
# ====================
@comms.callback()
def main(
    verbose: Annotated[
        bool,
        typer.Option("-v", "--verbose", help="Show progress in terminal.", rich_help_panel="Options")
    ] = False,
    debug: Annotated[
        bool,
        typer.Option("-vv", "--debug", help="Show debug messages in terminal (implies --verbose).", rich_help_panel="Options")
    ] = False,
):
    if debug:
        log_level = logging.DEBUG
    elif verbose:
        log_level = logging.INFO
    else:
        log_level = logging.WARN
    logging.basicConfig(
        format='%(asctime)s %(levelname)-10s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=log_level,
    )