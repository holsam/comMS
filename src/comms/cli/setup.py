'''
comMS CLI subcommand for setup (downloading tools) '''

# -- Import external dependencies
import typer
from pathlib import Path
from typing import Annotated, Literal, Optional

# -- Import internal dependencies
from comms.commands import setup as setupFuncs
from comms.utils.download import CRUX_DEFAULT_VERSION, TRFP_DEFAULT_VERSION

# -- Initialise setup Typer class
toolSetup = typer.Typer(add_completion=False)

# -- setup: download TRFP and/or Crux to config-defined bin directory
@toolSetup.command(help='Download ThermoRawFileParser and/or Crux to the configured bin directory', rich_help_panel='Utilities',
)
def setup(
    # Which tool(s) to download
    tool: Annotated[
        Literal['all', 'crux', 'trfp'],
        typer.Argument(
            help=('Tool to download'),
            show_choices=True,
            show_default=True,
        ),
    ] = 'all',
    # ThermoRawFileParser version override
    trfp_version: Annotated[
        str,
        typer.Option(
            '--trfp-version',
            help=(f'ThermoRawFileParser version to download'),
            show_default=True,
        ),
    ] = TRFP_DEFAULT_VERSION,
    # Crux version override
    crux_version: Annotated[
        str,
        typer.Option(
            '--crux-version',
            help=(
                f'Crux version to download'),
                show_default=True,
        ),
    ] = CRUX_DEFAULT_VERSION,
    # Bin directory override
    bin_dir: Annotated[
        Optional[Path],
        typer.Option(
            '--bin-dir',
            help=('Directory to install the downloaded tools'),
            file_okay=False,
            dir_okay=True,
            writable=True,
        ),
    ] = None,
    # Force re-download even if a binary already exists
    force: Annotated[
        bool,
        typer.Option(
            '--force',
            help=('Overwrite existing installations without prompting.'),
        ),
    ] = False,
) -> None:
    '''
    Download ThermoRawFileParser and/or the Crux toolkit
    '''
    try:
        setupFuncs.setup_tools(
            tool=tool,
            trfp_version=trfp_version,
            crux_version=crux_version,
            bin_dir=bin_dir,
            force=force,
        )
    except NotImplementedError:
        raise typer.Exit(1)
    except Exception:
        raise typer.Exit(1)