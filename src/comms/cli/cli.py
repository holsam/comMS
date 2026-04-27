'''
comMS ENTRYPOINT
'''

# -- Import external dependencies
import logging, typer
from typing import Annotated

# -- Import internal utility functions
from comms.utils.settings import initComms, lg

# -- Import comMS commands
from comms.cli.convert import commsConvert
from comms.cli.index import commsIndex
from comms.cli.search import commsSearch
from comms.cli.rescore import commsRescore
from comms.cli.quantify import commsQuantify
from comms.cli.report import commsReport
from comms.cli.pipeline import commsPipeline
from comms.cli.config import commsConfig
from comms.cli.version import commsVersion
from comms.cli.license import commsLicense

# -- Print startup splash
initComms()

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
comms.add_typer(commsPipeline)
comms.add_typer(commsConvert)
comms.add_typer(commsIndex)
comms.add_typer(commsSearch)
comms.add_typer(commsRescore)
comms.add_typer(commsQuantify)
comms.add_typer(commsReport)
comms.add_typer(commsConfig, name='config', help='Manage comMS configuration', rich_help_panel='Utilities')
comms.add_typer(commsVersion)
comms.add_typer(commsLicense)


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