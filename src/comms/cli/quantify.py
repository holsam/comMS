'''
comMS CLI subcommand for spectral counting quantification
'''

# -- Import external dependencies
import typer
from pathlib import Path
from typing import Annotated, Literal, Optional

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
    measure: Annotated[
        Optional[Literal['NSAF', 'dNSAF', 'EMPAI', 'SIN']],
        typer.Option('--measure', help='Spectral-counting measure [dim][default: config quantify.measure][/dim]')
    ] = None,
    qvalue_threshold: Annotated[
        Optional[float],
        typer.Option('--qvalue-threshold', help='PSM q-value threshold for inclusion [dim][default: config quantify.qvalue_threshold][/dim]', min=0.0, max=1.0)
    ] = None,
    unique_mapping: Annotated[
        Optional[bool],
        typer.Option('--unique-mapping/--no-unique-mapping', help='Require unique peptide-to-protein mapping [dim][default: config quantify.unique_mapping][/dim]')
    ] = None,
):
    ctx = ExperimentContext.resolve(experiment_dir)
    quantifyFuncs.run_quantify(
        psm_dir,
        database,
        ctx,
        measure=measure,
        qvalue_threshold=qvalue_threshold,
        unique_mapping=unique_mapping,
    )