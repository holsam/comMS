'''
comMS CLI subcommand for rescoring PSMs using Percolator
'''

# -- Import external dependencies
import typer
from pathlib import Path
from typing import Annotated, Optional

# -- Import internal functions
from comms.commands import rescore as rescoreFuncs
from comms.utils.context import ExperimentContext

# -- Initialise rescore Typer class
commsRescore = typer.Typer(add_completion=False)

# -- rescore: rescores PSMs from search using Percolator with picked-protein FDR, requiring at least two unique peptides per protein for confident identification
@commsRescore.command(help='Rescore PSMs using Percolator', rich_help_panel='Protein Identification')
def rescore(
    psm_dir: Annotated[
        Optional[Path],
        typer.Option('-p', '--psm-dir', help='Directory containing target PSM files [dim][default: search results][/dim]')
    ] = None,
    database: Annotated[
        Optional[Path],
        typer.Option('-f', '--fasta', help='Path to FASTA file [dim][default: experiment database file][/dim]')
    ] = None,
    organism_tags: Annotated[
        Optional[str],
        typer.Option('-o', '--organism-tags', help='Patterns to split FASTA file by organism (e.g. "org1, <pattern1>, org2, <pattern2>") [dim][default: config organism tags][/dim]')
    ] = None,
    experiment_dir: Annotated[
        Optional[Path],
        typer.Option('-e', '--experiment-dir', help='Experiment directory', exists=True, file_okay=False, dir_okay=True, writable=True)
    ] = Path('.'),
):
    ctx = ExperimentContext.resolve(experiment_dir)
    rescoreFuncs.run_rescore(psm_dir, database, ctx, organism_tags)