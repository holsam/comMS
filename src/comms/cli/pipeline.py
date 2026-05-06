'''
comMS CLI subcommand for running entire pipeline
'''

# -- Import external dependencies
import typer
from pathlib import Path
from typing import Annotated

# -- Import internal functions
from comms.commands import pipeline as pipelineFuncs
from comms.utils.settings import config

# -- Initialise pipeline Typer class
commsPipeline = typer.Typer(add_completion=False)

# -- pipeline: runs the full comMS pipeline
@commsPipeline.command(help='Run the comMS pipeline end-to-end', rich_help_panel='Pipeline')
def pipeline(
    sample_sheet: Annotated[
        Path,
        typer.Argument(help='Path to the comMS sample sheet (TSV/CSV)', exists=True, file_okay=True, dir_okay=False, readable=True)
    ],
    database: Annotated[
        Path,
        typer.Option('-d', '--database', help='Path to proteome FASTA', exists=True, file_okay=True, dir_okay=False)
    ],
    input: Annotated[
        Path,
        typer.Option('-i', '--input', help='Directory containing .RAW or .mzML files', exists=True, file_okay=False, dir_okay=True)
    ],
    organism_tags: Annotated[
        str,
        typer.option('--organism-tags', help='Comma-separated patterns to use for splitting FASTA file by organism (e.g. "org1, <pattern1>, org2, <pattern2>")')
    ],
    output: Annotated[
        Path | None,
        typer.Option('-o', '--out-dir', help='Root output directory', file_okay=False, dir_okay=True, writable=True)
    ] = Path('.'),
    param_medic: Annotated[
        bool,
        typer.Option('--param-medic', help='Run param-medic to estimate mass tolerances before searching')
    ] = False,
    skip_convert: Annotated[
        bool,
        typer.Option('--skip-convert', help='Skip the .RAW conversion step (use if mzML files are already available)')
    ] = False,
    skip_report: Annotated[
        bool,
        typer.Option('--skip-report', help='Skip the report generation step')
    ] = False,
    threads: Annotated[
        int,
        typer.Option('--threads', help='Number of threads to use', min=1)
    ] = config['search']['threads'],
):
    pipelineFuncs.run_pipeline(
        sample_sheet=sample_sheet,
        database=database,
        input_dir=input,
        output_dir=output,
        param_medic=param_medic,
        skip_convert=skip_convert,
        skip_report=skip_report,
        threads=threads,
        org_tags=organism_tags,
    )