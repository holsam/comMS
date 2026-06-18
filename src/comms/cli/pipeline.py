'''
comMS CLI subcommand for running entire pipeline
'''

# -- Import external dependencies
import typer
from pathlib import Path
from typing import Annotated, Optional

# -- Import internal functions
from comms.commands import pipeline as pipelineFuncs
from comms.utils.context import ExperimentContext

# -- Initialise pipeline Typer class
commsPipeline = typer.Typer(add_completion=False)

# -- pipeline: runs the full comMS pipeline
@commsPipeline.command(help='Run the comMS pipeline end-to-end', rich_help_panel='Pipelines')
def pipeline(
    sample_sheet: Annotated[
        Optional[Path],
        typer.Option('-s', '--sample-sheet', help='Path to sample sheet [dim][default: config sample sheet][/dim]')
    ] = None,
    database: Annotated[
        Optional[Path],
        typer.Option('-f', '--fasta', help='Path to FASTA file [dim][default: config database file][/dim]')
    ] = None,
    data: Annotated[
        Optional[list[Path]],
        typer.Option('-d', '--data', help='.mzML file(s) to search; repeatable [dim][default: convert results][/dim]')
    ] = None,
    organism_tags: Annotated[
        Optional[str],
        typer.Option('-o', '--organism-tags', help='Patterns to split FASTA file by organism (e.g. "org1, <pattern1>, org2, <pattern2>") [dim][default: config organism tags][/dim]')
    ] = None,
    experiment_dir: Annotated[
        Optional[Path],
        typer.Option('-e', '--experiment-dir', help='Experiment directory', exists=True, file_okay=False, dir_okay=True, writable=True)
    ] = Path('.'),
    param_medic: Annotated[
        bool,
        typer.Option('--param-medic', help='Run param-medic to estimate mass tolerances before searching')
    ] = False,
    skip_convert: Annotated[
        bool,
        typer.Option('--skip-convert', help='Skip the .RAW conversion step (use if mzML files are already available)')
    ] = False,
    skip_lfq: Annotated[
        bool,
        typer.Option('--skip-lfq', help='Skip MS1 label free quantification')
    ] = False,
    skip_quantify: Annotated[
        bool,
        typer.Option('--skip-quant', help='Skip dNSAF spectral counting quantification')
    ] = False,
    skip_report: Annotated[
        bool,
        typer.Option('--skip-report', help='Skip the report generation step')
    ] = False,
    threads: Annotated[
        int,
        typer.Option('--threads', help='Number of threads to use', min=1)
    ] = None,
):
    ctx = ExperimentContext.resolve(experiment_dir)
    pipelineFuncs.run_pipeline(
        sample_sheet=sample_sheet,
        database=database,
        data=data,
        ctx=ctx,
        param_medic=param_medic,
        skip_convert=skip_convert,
        skip_lfq=skip_lfq,
        skip_quantify=skip_quantify,
        skip_report=skip_report,
        threads=threads,
        org_tags=organism_tags,
    )