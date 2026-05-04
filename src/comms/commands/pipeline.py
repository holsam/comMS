'''
comMS pipeline functions
'''
# -- Import external dependencies
import datetime
from pathlib import Path
from rich import print

# -- Import internal functions
from comms.utils.log import logMsg
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
    log = logMsg('pipeline')
    START = datetime.datetime.now()
    print(f"\n[bold]comMS pipeline started:[/bold] {START.strftime('%Y-%m-%d %H:%M:%S')}\n")
    # -- Load sample sheet
    log.debug('Importing sample sheet')
    try:
        samples = loadSampleSheet(sample_sheet)
    except ValueError as e:
        print(f'[bold red]ERROR:[/bold red] {e}')
        raise SystemExit(1)
    print(f"Sample sheet loaded: {len(samples)} samples across {samples['treatment'].nunique()} treatment(s).")
    log.debug(f"Sample sheet loaded: {len(samples)} sample(s); {samples['treatment'].nunique()} treatment(s)")
    # -- Step 1: Convert (optional)
    if not skip_convert:
        log.debug(f'Starting .RAW conversion')
        print(f'\n[bold blue]Step 1/5:[/bold blue] Converting .RAW files...')
        convert.run_convert(input_dir=input_dir, output=output_dir, gzip=True, in_pipeline=True)
        mzml_dir = output_dir / 'comms/results/convert'
    else:
        print(f'\n[dim]Step 1/5: Skipping .RAW conversion (--skip-convert).[/dim]')
        mzml_dir = input_dir
    log.debug(f'mzml_dir: {mzml_dir}')
    # -- Step 2: Build index
    log.debug(f'Starting peptide indexing')
    print(f'\n[bold blue]Step 2/5:[/bold blue] Building peptide index...')
    index.run_index(database=database, output=output_dir, in_pipeline=True)
    index_dir = output_dir / 'comms/results/index'
    log.debug(f'index_dir: {index_dir}')
    # -- Step 3: Search
    log.debug(f'Starting peptide-spectra matching')
    print(f'\n[bold blue]Step 3/5:[/bold blue] Running Tide-search...')
    search.run_search(
        input_dir=mzml_dir,
        index_dir=index_dir,
        output=output_dir,
        param_medic=param_medic,
        threads=threads,
        in_pipeline=True
    )
    search_dir = output_dir / 'comms/results/search'
    log.debug(f'search_dir: {search_dir}')
    # -- Step 4: Rescore
    log.debug(f'Starting PSM rescoring')
    print(f'\n[bold blue]Step 4/5:[/bold blue] Running Percolator rescoring...')
    rescore.run_rescore(input_dir=search_dir, database=database, output=output_dir, in_pipeline=True)
    rescore_dir = output_dir / 'comms/results/rescore'
    log.debug(f'rescore_dir: {rescore_dir}')
    # -- Step 5: Quantify
    log.debug('Starting quantification')
    print(f'\n[bold blue]Step 5/5:[/bold blue] Running dNSAF spectral counting...')
    quantify.run_quantify(input_dir=rescore_dir, database=database, output=output_dir, in_pipeline=True)
    quantify_dir = output_dir / 'comms/results/quantify'
    log.debug(f'quantify_dir: {quantify_dir}')
    END = datetime.datetime.now()
    print(f'\n[bold green]Pipeline complete.[/bold green] Runtime: {END - START}')
    print(f'All results written to: {output_dir}\n')