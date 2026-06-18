'''
comMS CLI subcommand for generating report
'''

# -- Import external dependencies
import typer
from pathlib import Path
from typing import Annotated, Optional

# -- Import internal functions
from comms.commands import report as reportFuncs
from comms.utils.context import ExperimentContext

# -- Define constants (report sections)
VALID_SECTIONS = {'qc', 'pca', 'da', 'primary-species', 'secondary-species', 'concordance'}
DEFAULT_SECTIONS = ['qc', 'pca', 'da']

# -- Initialise report Typer class
commsReport = typer.Typer(add_completion=False)

# -- report: invokes the Quarto report (report.qmd) on quantification output
@commsReport.command(help='Generate a static report from quantification output', rich_help_panel='Downstream Analysis')
def report(
    organism_prefix: Annotated[
        Optional[str],
        typer.Option('-o', '--organism-prefix', help='ID prefix for the primary organism [dim][default: config organism prefix][/dim]')
    ] = None,
    quantify_dir: Annotated[
        Optional[Path],
        typer.Option('-q', '--quantify-dir', help='Path to quantification results [dim][default: quantify output][/dim]')
    ] = None,
    sample_sheet: Annotated[
        Optional[Path],
        typer.Option('-s', '--sample-sheet', help='Path to sample sheet [dim][default: config sample sheet][/dim]')
    ] = None,
    experiment_dir: Annotated[
        Optional[Path],
        typer.Option('-e', '--experiment-dir', help='Experiment directory', exists=True, file_okay=False, dir_okay=True, writable=True)
    ] = Path('.'),
    lfq_dir: Annotated[
        Optional[Path],
        typer.Option('-l', '--lfq-dir', help='Path to LFQ results [dim][default: lfq output][/dim]')
    ] = None,
    ref_info: Annotated[
        Optional[Path],
        typer.Option('-r', '--ref-info', help='Protein metadata TSV [dim][default: config ref_info][/dim]')
    ] = None,
    cont_csv: Annotated[
        Optional[Path],
        typer.Option('-c', '--cont-csv', help='Contaminant annotations CSV [dim][default: config cont_csv][/dim]')
    ] = None,
    min_reps: Annotated[
        int,
        typer.Option('--min-reps', help='Minimum replicates per fraction-treatment group', min=1)
    ] = 3,
    lfc_threshold: Annotated[
        float,
        typer.Option('--lfc-threshold', help='|log2FC| threshold for DA', min=0.0)
    ] = 1.0,
    fdr_threshold: Annotated[
        float,
        typer.Option('--fdr-threshold', help='BH-FDR threshold for DA', min=0.0, max=1.0)
    ] = 0.05,
    section: Annotated[
        Optional[list[str]],
        typer.Option('--section', help='Section(s) to run (repeatable)')
    ] = None,
    all_sections: Annotated[
        bool,
        typer.Option('--all', help='Run all sections')
    ] = False,
    overwrite: Annotated[
        bool,
        typer.Option('--overwrite', help='Overwrite existing output directory')
    ] = False,
    rscript: Annotated[
        str,
        typer.Option('--rscript', help='Path to Rscript binary')
    ] = 'Rscript',
):
    sections = list(VALID_SECTIONS) if all_sections else (section or DEFAULT_SECTIONS)
    invalid = set(sections) - VALID_SECTIONS
    ctx = ExperimentContext.resolve(experiment_dir)
    reportFuncs.run_report(
        quantify_dir=quantify_dir,
        sample_sheet=sample_sheet,
        ctx=ctx,
        lfq_dir=lfq_dir,
        ref_info=ref_info,
        cont_csv=cont_csv,
        organism_prefix=organism_prefix,
        min_reps=min_reps,
        lfc_threshold=lfc_threshold,
        fdr_threshold=fdr_threshold,
        sections=sections,
        overwrite=overwrite,
        rscript=rscript,
        in_pipeline=False
    )