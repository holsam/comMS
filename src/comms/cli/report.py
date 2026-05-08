'''
comMS CLI subcommand for generating report
'''

# -- Import external dependencies
import typer
from pathlib import Path
from typing import Annotated, Literal

# -- Import internal functions
from comms.commands import report as reportFuncs

# -- Initialise report Typer class
commsReport = typer.Typer(add_completion=False)

# -- report: invokes the Quarto report (report.qmd) on quantification output
@commsReport.command(help='Generate an HTML report from quantification output', rich_help_panel='Downstream Analysis')
def report(
    quantification: Annotated[
        Path,
        typer.Argument(help='Path to the spectral-counts output directory or merged TSV', exists=True)
    ],
    sample_sheet: Annotated[
        Path,
        typer.Option('-s', '--sample-sheet', help='Path to the comMS sample sheet (TSV/CSV)', exists=True, file_okay=True, dir_okay=False)
    ],
    output: Annotated[
        Path | None,
        typer.Option('-o', '--out-dir', help='Output directory for the rendered report', file_okay=False, dir_okay=True, writable=True)
    ] = Path('.'),
    format: Annotated[
        Literal["html", "pdf"],
        typer.Option('-f', '--format', help='Report output format (html, pdf)')
    ] = 'html',
):
    reportFuncs.run_report(quantification, sample_sheet, output, format)