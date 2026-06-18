'''
comMS CLI subcommand for indexing proteomes
'''

# -- Import external dependencies
import typer
from pathlib import Path
from typing import Annotated, Optional

# -- Import internal functions
from comms.commands import lfq as lfqFuncs
from comms.utils.context import ExperimentContext

# -- Initialise index Typer class
commsLfq = typer.Typer(add_completion=False)

# -- index: builds a peptide index from a pre-merged combined FASTA database using peptide-level reverse decoys and modifications defined in config.toml
@commsLfq.command(help='Run MS1 label-free quantification', rich_help_panel='Protein Identification')
def lfq(
    data: Annotated[
        Optional[list[Path]],
        typer.Option('-d', '--data', help='.mzML file(s); repeatable [dim][default: convert results][/dim]')
    ] = None,
    psm_dir: Annotated[
        Optional[Path],
        typer.Option('-p', '--psm-dir', help='Path to directory containing rescored PSM files [dim][default: rescore results][/dim]')
    ] = None,
    sample_sheet: Annotated[
        Optional[Path],
        typer.Option('-s', '--sample-sheet', help='Path to sample sheet [dim][default: experiment sample sheet][/dim]')
    ] = None,
    experiment_dir: Annotated[
        Optional[Path],
        typer.Option('-e', '--experiment-dir', help='Experiment directory')
    ] = Path('.'),
):
    ctx = ExperimentContext.resolve(experiment_dir)
    lfqFuncs.run_lfq(psm_dir, data, sample_sheet, ctx)