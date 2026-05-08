'''
comMS CLI subcommand for indexing proteomes
'''

# -- Import external dependencies
import typer
from pathlib import Path
from typing import Annotated

# -- Import internal functions
from comms.commands import index as indexFuncs

# -- Initialise index Typer class
commsIndex = typer.Typer(add_completion=False)

# -- index: builds a peptide index from a pre-merged combined FASTA database using peptide-level reverse decoys and modifications defined in config.toml
@commsIndex.command(help='Generate a peptide index from a FASTA file', rich_help_panel='Protein Identification')
def index(
    database: Annotated[
        Path,
        typer.Argument(
            help='Path to FASTA file',
            exists=True, file_okay=True, dir_okay=False, readable=True
        )
    ],
    output: Annotated[
        Path | None,
        typer.Option('-o', '--out-dir', help='Output directory for peptide index', file_okay=False, dir_okay=True, writable=True)
    ] = Path('.'),
):
    indexFuncs.run_index(database, output)