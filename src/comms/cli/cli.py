'''
comMS ENTRYPOINT
'''

# -- Import external dependencies
import logging, typer
from typing import Annotated

# -- Import internal utility functions
from comms.utils.settings import initComms
from comms.utils.log import configureStreamLogging, log_state, PROGRESS

# -- Import comMS CLI typers (and experiment)
from comms.cli.convert import commsConvert
from comms.cli.index import commsIndex
from comms.cli.lfq import commsLfq
from comms.cli.search import commsSearch
from comms.cli.rescore import commsRescore
from comms.cli.quantify import commsQuantify
from comms.cli.report import commsReport
from comms.cli.pipeline import commsPipeline
from comms.cli.config import commsConfig
from comms.cli.license import commsLicense
from comms.cli.uninstall import commsUninstall
from comms.cli.version import commsVersion

# Import comMS experiment functions
from comms.commands import experiment as experimentFuncs

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
comms.add_typer(commsLfq)
comms.add_typer(commsQuantify)
comms.add_typer(commsReport)
comms.add_typer(commsConfig, name='config', help='Manage comMS configuration', rich_help_panel='Utilities')
comms.add_typer(commsLicense)
comms.add_typer(commsUninstall)
comms.add_typer(commsVersion)

# -- Register experiment command
@comms.command(rich_help_panel='Utilities')
def experiment(
    headless: Annotated[
        bool,
        typer.Option('--headless', help='Run setup in terminal instead of GUI')
    ] = False,
):
    '''Set up a comMS experiment (sample sheet + config + metadata)'''
    if headless:
        experimentFuncs.run_experiment_headless()
    else:
        experimentFuncs.launch_experiment_gui()

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
        log_level = PROGRESS
    else:
        log_level = logging.INFO
    log_state.log_level = log_level
    configureStreamLogging()