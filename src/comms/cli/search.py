'''
comMS CLI subcommand for peptide-spectra searching
'''

# -- Import external dependencies
import typer
from pathlib import Path
from typing import Annotated

# -- Import internal functions
from comms.commands import search as searchFuncs
from comms.utils.context import ExperimentContext

# -- Initialise search Typer class
commsSearch = typer.Typer(add_completion=False)

# -- search: runs Crux Tide-search on all mzML files in the input directory, optionally runs param-medic first to estimate mass tolerances; falls back to config.toml defaults
@commsSearch.command(help='Match spectra to peptides using tide-search', rich_help_panel='Protein Identification')
def search(
    input: Annotated[
        Path,
        typer.Argument(help='Directory of .mzML files to search', exists=True, file_okay=False, dir_okay=True, readable=True)
    ],
    index: Annotated[
        Path,
        typer.Option('-i', '--index', help='Path to the peptide index directory', exists=True, file_okay=False, dir_okay=True)
    ],
    experiment_dir: Annotated[
        Path | None,
        typer.Option('-e', '--experiment-dir', help='Experiment directory', exists=True, file_okay=False, dir_okay=True, writable=True)
    ] = Path('.'),
    param_medic: Annotated[
        bool,
        typer.Option('--param-medic', help='Run param-medic to estimate mass tolerances from data before searching')
    ] = False,
    threads: Annotated[
        int,
        typer.Option('--threads', help='Number of threads to use', min=1)
    ] = None,
):
    ctx = ExperimentContext.resolve(experiment_dir)
    searchFuncs.run_search(input, index, ctx, param_medic, threads)