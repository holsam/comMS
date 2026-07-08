'''
comMS CLI subcommand for managing R dependencies
'''

# -- Import external dependencies
import typer
from typing import Annotated, List, Optional

# -- Import internal functions
from comms.utils import installrdeps as rUtils
from comms.utils.log import logMsg

# -- Initialise Typer class
commsRUtils = typer.Typer(add_completion=False, invoke_without_command=True)

# -- Define rUtils callback
@commsRUtils.callback(invoke_without_command=False)
def rutils_callback(ctx: typer.Context) -> None:
    logMsg('r-utils')

# -- Define R utility command: check
@commsRUtils.command(rich_help_panel='R Utilities')
def check():
    '''Check that all required R dependencies are installed'''
    rUtils.check_r_dependencies()

# -- Define R utility command: install
@commsRUtils.command(rich_help_panel='R Utilities')
def install():
    '''Install any missing R dependencies'''
    rUtils.install_r_dependencies_terminal()