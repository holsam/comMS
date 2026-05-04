'''
comMS report functions
'''

# -- Import external dependencies
import shutil, subprocess
from pathlib import Path
from rich import print

# -- Import internal functions
from comms.utils.log import logMsg
from comms.utils.settings import config
from comms.utils import paths as pathutil

# -- run_report: return message saying report is not functional at this time
def run_report(quantification: Path, sample_sheet: Path, output: Path, fmt: str):
    log = logMsg('report')
    log.warn('Report functionality is not yet supported')
    raise NotImplementedError()

# -- run_report: renders the comMS Quarto report from quantification output and writes it to output
# def run_report(quantification: Path, sample_sheet: Path, output: Path, fmt: str):
#     lg.debug('report | Checking for Quarto installation...')
#     quarto = shutil.which('quarto')
#     if quarto is None:
#         print(f'[bold red]ERROR:[/bold red] Quarto not found. Install Quarto from https://quarto.org before running this command.')
#         raise SystemExit(1)
#     lg.debug('report | Checking for R installation...')
#     rscript = shutil.which('Rscript')
#     if rscript is None:
#         print(f'[bold red]ERROR:[/bold red] Rscript not found. R is required for report generation.')
#         raise SystemExit(1)
#     # -- Locate bundled report.qmd
#     from importlib.resources import files as pkg_files
#     qmd_path = pkg_files('comms').joinpath('report/report.qmd')
#     out_dir = pathutil.generateOutputFileStructure(output, 'report')
#     print(f'\nGenerating comMS report...')
#     print(f'- Quantification input: {quantification}')
#     print(f'- Sample sheet: {sample_sheet}')
#     print(f'- Output format: {fmt}')
#     print(f'- Output directory: {out_dir}')
#     cmd = [
#         quarto, 'render', str(qmd_path),
#         '--output-dir', str(out_dir),
#         '--to', fmt,
#         '-P', f'quantification_path:{quantification}',
#         '-P', f'sample_sheet_path:{sample_sheet}',
#         '-P', f"top_n:{config['report']['top_n_proteins']}",
#         '-P', f"fdr_threshold:{config['report']['fdr_threshold']}",
#     ]
#     lg.debug(f"report | Running: {' '.join(cmd)}")
#     result = subprocess.run(cmd, check=False)
#     if result.returncode != 0:
#         print(f'[bold red]ERROR:[/bold red] Quarto render failed. Check the output above for details.')
#         raise SystemExit(1)
#     print(f'\n[bold green]SUCCESS:[/bold green] Report written to {out_dir}\n')