'''
comMS CLI subcommand for spectral counting quantification
'''

# -- Import external dependencies
import typer
from pathlib import Path
from typing import Annotated

# -- Import internal functions
from comms.commands import quantify as quantifyFuncs
from comms.utils.settings import ExperimentContext

# -- Initialise quantify Typer class
commsQuantify = typer.Typer(add_completion=False)

# -- quantify: runs crux spectral-counts using dNSAF on Percolator output
@commsQuantify.command(help='Run dNSAF spectral counting on Percolator output', rich_help_panel='Protein Identification')
def quantify(
    input: Annotated[
        Path,
        typer.Argument(help='Directory containing Percolator PSM output files', exists=True, file_okay=False, dir_okay=True, readable=True)
    ],
    database: Annotated[
        Path,
        typer.Option('-d', '--database', help='Path to proteome FASTA', exists=True, file_okay=True, dir_okay=False)
    ],
    experiment_dir: Annotated[
        Path | None,
        typer.Option('-e', '--experiment-dir', help='Experiment directory', exists=True, file_okay=False, dir_okay=True, writable=True)
    ] = Path('.'),
):
    ctx = ExperimentContext.resolve(experiment_dir)
    quantifyFuncs.run_quantify(input, database, ctx)