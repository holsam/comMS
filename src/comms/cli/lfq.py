'''
comMS CLI subcommand for indexing proteomes
'''

# -- Import external dependencies
import typer
from pathlib import Path
from typing import Annotated

# -- Import internal functions
from comms.commands import lfq as lfqFuncs
from comms.utils.settings import ExperimentContext

# -- Initialise index Typer class
commsLfq = typer.Typer(add_completion=False)

# -- index: builds a peptide index from a pre-merged combined FASTA database using peptide-level reverse decoys and modifications defined in config.toml
@commsLfq.command(help='Run MS1 label-free quantification', rich_help_panel='Protein Identification')
def lfq(
    psm_dir: Annotated[
        Path,
        typer.Option('-p', '--psm-dir', help='Path to directory containing rescored PSM files', exists=True, file_okay=False, dir_okay=True, readable=True)
    ],
    mzml_dir: Annotated[
        Path,
        typer.Option('-m', '--mzml-dir', help='Path to directory containing .mzML files', exists=True, file_okay=False, dir_okay=True, readable=True)
    ],
    sample_sheet: Annotated[
        Path,
        typer.Option('-s', '--sample-sheet', help='Path to sample sheet', exists=True, file_okay=True, dir_okay=False, readable=True)
    ],
    experiment_dir: Annotated[
        Path | None,
        typer.Option('-e', '--experiment-dir', help='Experiment directory', exists=True, file_okay=False, dir_okay=True, writable=True)
    ] = Path('.'),
):
    ctx = ExperimentContext.resolve(experiment_dir)
    lfqFuncs.run_lfq(psm_dir, mzml_dir, sample_sheet, ctx)