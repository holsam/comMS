'''
comMS CLI subcommand for file conversion
'''

# -- Import external dependencies
import typer
from pathlib import Path
from typing import Annotated, Optional

# -- Import internal functions
from comms.commands import convert as convertFuncs
from comms.utils.context import ExperimentContext

# -- Initialise convert Typer class
commsConvert = typer.Typer(add_completion=False)

# -- convert: converts all .RAW files in the input directory to indexed mzML using ThermoRawFileParser
@commsConvert.command(help='Convert .RAW files to indexed .mzML', rich_help_panel='Protein Identification')
def convert(
    data: Annotated[
        Optional[list[Path]],
        typer.Option('-d', '--data', help='.RAW file(s) to convert; repeatable [dim][default: experiment data files][/dim]')
    ] = None,
    experiment_dir: Annotated[
        Optional[Path],
        typer.Option('-e', '--experiment-dir', help='Experiment directory', exists=True, file_okay=False, dir_okay=True, writable=True)
    ] = Path('.'),
    gzip: Annotated[
        Optional[bool],
        typer.Option('--gzip/--no-gzip', help='Gzip-compress mzML output file(s)')
    ] = None,
):
    ctx = ExperimentContext.resolve(experiment_dir)
    convertFuncs.run_convert(data, ctx, gzip)