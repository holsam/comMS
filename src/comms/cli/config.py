'''
comMS CLI subcommand for managing configuration files
'''

# -- Import external dependencies
import typer
from typing import Annotated, Optional

# -- Import internal functions
from comms.commands import config as configFuncs

# -- Initialise config Typer class
commsConfig = typer.Typer(add_completion=False, invoke_without_command=True)

# -- Define config callback
@commsConfig.callback(invoke_without_command=True)
def config_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        configFuncs.config_exists()

# -- Define config command: init
@commsConfig.command(rich_help_panel='Config Commands')
def init():
    '''Create a user config file with default settings in the OS config directory'''
    configFuncs.config_init()

# -- Define config command: exists
@commsConfig.command(rich_help_panel='Config Commands')
def exists():
    '''Report whether a user config file exists and print its path'''
    configFuncs.config_exists()

# -- Define config command: list
@commsConfig.command(rich_help_panel='Config Commands')
def list():
    '''Print current config values, highlighting differences from bundled defaults'''
    configFuncs.config_list()

# -- Define config command: verify
@commsConfig.command(rich_help_panel='Config Commands')
def verify():
    '''Check that all expected keys are present in the user config file'''
    configFuncs.config_verify()

# -- Define config command: reset
@commsConfig.command(rich_help_panel='Config Commands')
def reset(
    force: Annotated[
        bool,
        typer.Option('--force', help='Skip confirmation and immediately overwrite config.toml')
    ] = False
):
    '''Overwrite the user config file with comMS built-in defaults'''
    configFuncs.config_reset(force=force)

# -- Define config command: set
@commsConfig.command(rich_help_panel='Config Commands')
def set(
    iodo: Annotated[
        Optional[bool],
        typer.Option(
            '--iodo/--no-iodo',
            help=('Add (--iodo) or remove (--no-iodo) static carbamidomethylation of cysteine as a static modification.'),
        ),
    ] = None,
):
    '''
    Set values in user configuration file
    '''
    configFuncs.config_set(iodo=iodo)