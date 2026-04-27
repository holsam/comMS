'''
comMS CLI subcommand for displaying comMS version
'''

# -- Import external dependencies
import typer

# -- Import internal functions
from comms.commands import version as versionFuncs

# -- Initialise version Typer class
commsVersion = typer.Typer(add_completion=False, add_help_option=False)

# -- version: prints the current comMS version to terminal and exits
@commsVersion.command(help='Print current comMS version', rich_help_panel='Utilities')
def version():
    versionFuncs.printVersion()