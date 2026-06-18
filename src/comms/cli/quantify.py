'''
comMS CLI subcommand for spectral counting quantification
'''

# -- Import external dependencies
import typer
from pathlib import Path
from typing import Annotated, Optional

# -- Import internal functions
from comms.commands import quantify as quantifyFuncs
from comms.utils.context import ExperimentContext

# -- Initialise quantify Typer class
commsQuantify = typer.Typer(add_completion=False)

# -- quantify: runs crux spectral-counts using dNSAF on Percolator output
@commsQuantify.command(help='Run dNSAF spectral counting on Percolator output', rich_help_panel='Protein Identification')
def quantify(
    psm_dir: Annotated[
        Optional[Path],
        typer.Option('-p', '--psm-dir', help='Directory containing Percolator PSM output files [dim][default: rescore output][/dim]')
    ] = None,
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
    quantifyFuncs.run_quantify(psm_dir, database, ctx)