'''
comMS CLI subcommand for indexing proteomes
'''

# -- Import external dependencies
import typer
from pathlib import Path
from typing import Annotated, Optional

# -- Import internal functions
from comms.commands import index as indexFuncs
from comms.utils.context import ExperimentContext

# -- Initialise index Typer class
commsIndex = typer.Typer(add_completion=False)

# -- index: builds a peptide index from a pre-merged combined FASTA database using peptide-level reverse decoys and modifications defined in config.toml
@commsIndex.command(help='Generate a peptide index from a FASTA file', rich_help_panel='Protein Identification')
def index(
    database: Annotated[
        Optional[Path],
        typer.Option('-f', '--fasta', help='Path to FASTA file [dim][default: experiment database file][/dim]')
    ] = None,
    experiment_dir: Annotated[
        Optional[Path],
        typer.Option('-e', '--experiment-dir', help='Experiment directory', exists=True, file_okay=False, dir_okay=True, writable=True)
    ] = Path('.'),
):
    ctx = ExperimentContext.resolve(experiment_dir)
    indexFuncs.run_index(database, ctx)