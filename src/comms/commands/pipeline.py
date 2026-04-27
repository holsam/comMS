'''
comMS pipeline functions
'''
# -- Import external dependencies
import datetime
from pathlib import Path
from rich import print

# -- Import internal functions
from comms.utils.settings import lg
from comms.utils.samples import loadSampleSheet
from comms.commands import convert, index, search, rescore, quantify, report

# -- run_pipeline: runs the full comMS pipeline end-to-end from a sample sheet
def run_pipeline(
    sample_sheet: Path,
    database: Path,
    input_dir: Path,
    output_dir: Path,
    param_medic: bool,
    skip_convert: bool,
    skip_report: bool,
    threads: int,
):
    START = datetime.datetime.now()
    print(f"\n[bold]comMS pipeline started:[/bold] {START.strftime('%Y-%m-%d %H:%M:%S')}\n")
    # -- Load sample sheet
    lg.debug('pipeline | Loading sample sheet...')
    try:
        samples = loadSampleSheet(sample_sheet)
    except ValueError as e:
        print(f'[bold red]ERROR:[/bold red] {e}')
        raise SystemExit(1)
    print(f"Sample sheet loaded: {len(samples)} samples across {samples['treatment'].nunique()} treatment(s).")
    # -- Step 1: Convert (optional)
    if not skip_convert:
        print(f'\n[bold blue]Step 1/5:[/bold blue] Converting .RAW files...')
        convert.run_convert(input_dir=input_dir, output=output_dir, gzip=True)
        mzml_dir = output_dir / 'comms/results/convert'
    else:
        print(f'\n[dim]Step 1/5: Skipping .RAW conversion (--skip-convert).[/dim]')
        mzml_dir = input_dir
    # -- Step 2: Build index
    print(f'\n[bold blue]Step 2/5:[/bold blue] Building peptide index...')
    index.run_index(database=database, output=output_dir)
    index_dir = output_dir / 'comms/results/index'
    # -- Step 3: Search
    print(f'\n[bold blue]Step 3/5:[/bold blue] Running Tide-search...')
    search.run_search(
        input_dir=mzml_dir,
        index_dir=index_dir,
        output=output_dir,
        param_medic=param_medic,
        threads=threads,
    )
    search_dir = output_dir / 'comms/results/search'
    # -- Step 4: Rescore
    print(f'\n[bold blue]Step 4/5:[/bold blue] Running Percolator rescoring...')
    rescore.run_rescore(input_dir=search_dir, database=database, output=output_dir)
    rescore_dir = output_dir / 'comms/results/rescore'
    # -- Step 5: Quantify
    print(f'\n[bold blue]Step 5/5:[/bold blue] Running dNSAF spectral counting...')
    quantify.run_quantify(input_dir=rescore_dir, database=database, output=output_dir)
    quantify_dir = output_dir / 'comms/results/quantify'
    # -- Step 6: Report (optional)
    if not skip_report:
        print(f'\n[bold blue]Report:[/bold blue] Generating HTML report...')
        report.run_report(
            quantification=quantify_dir,
            sample_sheet=sample_sheet,
            output=output_dir,
            fmt='html',
        )
    END = datetime.datetime.now()
    print(f'\n[bold green]Pipeline complete.[/bold green] Runtime: {END - START}')
    print(f'All results written to: {output_dir}\n')