'''
comMS CLI subcommand for generating report
'''

# -- Import external dependencies
import typer
from pathlib import Path
from typing import Annotated, Optional

# -- Import internal functions
from comms.commands import report as reportFuncs

# -- Define constants (report sections)
VALID_SECTIONS = {'qc', 'pca', 'da', 'primary-species', 'secondary-species', 'concordance'}
DEFAULT_SECTIONS = ['qc', 'pca', 'da']

# -- Initialise report Typer class
commsReport = typer.Typer(add_completion=False)

# -- report: invokes the Quarto report (report.qmd) on quantification output
@commsReport.command(help='Generate a static report from quantification output', rich_help_panel='Downstream Analysis')
def report(
    quantify_dir: Annotated[
        Path,
        typer.Argument(help='comms/results/quantify/ output directory', exists=True, file_okay=False, dir_okay=True)
    ],
    sample_sheet: Annotated[
        Path,
        typer.Argument(help='Sample sheet TSV/CSV used in the pipeline run', exists=True, file_okay=True, dir_okay=False)
    ],
    organism_prefix: Annotated[
        str,
        typer.Option('--organism-prefix', help='ID prefix for the primary organism')
    ],
    output: Annotated[
        Path,
        typer.Argument(help='Directory to write report outputs into')
    ] = Path('.'),
    lfq_dir: Annotated[
        Optional[Path],
        typer.Option('--lfq-dir', help='comms/results/lfq/ output directory from comms lfq')
    ] = None,
    ref_info: Annotated[
        Optional[Path],
        typer.Option('--ref-info', help='Protein metadata TSV')
    ] = None,
    cont_csv: Annotated[
        Optional[Path],
        typer.Option('--cont-csv', help='Contaminant annotations CSV')
    ] = None,
    min_reps: Annotated[
        int,
        typer.Option('--min-reps', help='Minimum replicates per fraction-treatment group', min=1)
    ] = 2,
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
    reportFuncs.run_report(
        quantify_dir=quantify_dir,
        sample_sheet=sample_sheet,
        output_dir=output,
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