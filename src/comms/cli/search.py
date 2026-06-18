'''
comMS CLI subcommand for peptide-spectra searching
'''

# -- Import external dependencies
import typer
from pathlib import Path
from typing import Annotated, Optional

# -- Import internal functions
from comms.commands import search as searchFuncs
from comms.utils.context import ExperimentContext

# -- Initialise search Typer class
commsSearch = typer.Typer(add_completion=False)

# -- search: runs Crux Tide-search on all mzML files in the input directory, optionally runs param-medic first to estimate mass tolerances; falls back to config.toml defaults
@commsSearch.command(help='Match spectra to peptides using tide-search', rich_help_panel='Protein Identification')
def search(
    data: Annotated[
        Optional[list[Path]],
        typer.Option('-d', '--data', help='.mzML file(s) to search; repeatable [dim][default: convert results][/dim]')
    ] = None,
    index: Annotated[
        Optional[Path],
        typer.Option('-i', '--index', help='Peptide index directory [dim][default: index results][/dim]')
    ] = None,
    experiment_dir: Annotated[
        Optional[Path],
        typer.Option('-e', '--experiment-dir', help='Experiment directory', exists=True, file_okay=False, dir_okay=True, writable=True)
    ] = Path('.'),
    param_medic: Annotated[
        bool,
        typer.Option('--param-medic', help='Estimate tolerances before searching')
    ] = False,
    threads: Annotated[
        int,
        typer.Option('--threads', help='Number of threads', min=1)
    ] = None,
):
    ctx = ExperimentContext.resolve(experiment_dir)
    searchFuncs.run_search(data, index, ctx, param_medic, threads)