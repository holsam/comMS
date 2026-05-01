'''
comMS CLI subcommand for displaying comMS license
'''

# -- Import external dependencies
import typer

# -- Import internal functions
from comms.commands import license as licenseFuncs

# -- Initialise license Typer class
commsLicense = typer.Typer(add_completion=False, add_help_option=False)

# -- license: prints the comMS license to terminal and exits
@commsLicense.command(help='Print comMS license', rich_help_panel='Utilities')
def license():
    licenseFuncs.printLicense()