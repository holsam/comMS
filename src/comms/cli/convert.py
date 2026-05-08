'''
comMS CLI subcommand for file conversion
'''

# -- Import external dependencies
import typer
from pathlib import Path
from typing import Annotated

# -- Import internal functions
from comms.commands import convert as convertFuncs
from comms.utils.settings import config

# -- Initialise convert Typer class
commsConvert = typer.Typer(add_completion=False)

# -- convert: converts all .RAW files in the input directory to indexed mzML using ThermoRawFileParser
@commsConvert.command(help='Convert .RAW files to indexed .mzML', rich_help_panel='Protein Identification')
def convert(
    input: Annotated[
        Path,
        typer.Argument(help='Directory containing .RAW files', exists=True, file_okay=False, dir_okay=True, readable=True)
    ],
    output: Annotated[
        Path | None,
        typer.Option('-o', '--out-dir', help='Output directory for .mzML file(s)', file_okay=False, dir_okay=True, writable=True)
    ] = Path('.'),
    gzip: Annotated[
        bool,
        typer.Option('--gzip/--no-gzip', help='Gzip-compress mzML output file(s)')
    ] = config['convert']['gzip'],
):
    convertFuncs.run_convert(input, output, gzip)