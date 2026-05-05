'''
comMS CLI subcommand for rescoring PSMs using Percolator
'''

# -- Import external dependencies
import typer
from pathlib import Path
from typing import Annotated

# -- Import internal functions
from comms.commands import rescore as rescoreFuncs

# -- Initialise rescore Typer class
commsRescore = typer.Typer(add_completion=False)

# -- rescore: rescores PSMs from search using Percolator with picked-protein FDR, requiring at least two unique peptides per protein for confident identification
@commsRescore.command(help='Rescore PSMs using Percolator', rich_help_panel='Commands')
def rescore(
    input: Annotated[
        Path,
        typer.Argument(help='Directory containing target PSM files', exists=True, file_okay=False, dir_okay=True, readable=True)
    ],
    database: Annotated[
        Path,
        typer.Option('-d', '--database', help='Path to proteome FASTA (required for picked-protein FDR)', exists=True, file_okay=True, dir_okay=False)
    ],
    organism_tags: Annotated[
        str,
        typer.option('--organism-tags', help='Patterns to use for splitting FASTA file by organism (e.g. "org1, <pattern1>, org2, <pattern2>")')
    ],
    output: Annotated[
        Path | None,
        typer.Option('-o', '--out-dir', help='Output directory', file_okay=False, dir_okay=True, writable=True)
    ] = Path('.'),
):
    rescoreFuncs.run_rescore(input, database, output, organism_tags)