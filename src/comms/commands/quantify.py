'''
comMS quantify functions
'''

# -- Import external dependencies
from pathlib import Path
from rich import print
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

# -- Import internal functions
from comms.utils.settings import config, lg
from comms.utils import crux as cruxutil
from comms.utils import paths as pathutil

# -- run_quantify: runs dNSAF spectral counting on all Percolator PSM files in input_dir and writes results to output
def run_quantify(input_dir: Path, database: Path, output: Path):
    lg.debug('quantify | Locating Crux binary...')
    bin_dir = Path(__file__).parents[4] / 'bin'
    crux_bin = cruxutil.findCrux(bin_dir)
    if crux_bin is None:
        print(f'[bold red]ERROR:[/bold red] Crux binary not found under {bin_dir}.')
        raise SystemExit(1)
    psm_files = sorted(input_dir.glob('*.percolator.psms.txt'))
    if not psm_files:
        print(f'[bold red]ERROR:[/bold red] No Percolator PSM files found in {input_dir}.')
        raise SystemExit(1)
    out_dir = pathutil.generateOutputFileStructure(output, 'quantify')
    log_path = out_dir.parent / 'quantify.log'
    print(f'\nRunning dNSAF spectral counting on {len(psm_files)} file(s)...')
    n_ok, n_fail = 0, 0
    with logging_redirect_tqdm():
        for psm_file in tqdm(psm_files, desc='Files quantified'):
            fileroot = psm_file.name.removesuffix('.percolator.psms.txt')
            ok = cruxutil.spectralCounts(
                crux_bin=crux_bin,
                psm_file=psm_file,
                database=database,
                out_dir=out_dir,
                fileroot=fileroot,
                config=config,
                log_path=log_path,
            )
            if ok:
                n_ok += 1
            else:
                lg.warning(f'quantify | spectral-counts failed for {psm_file.name}.')
                n_fail += 1
    print(f'\n[bold]Quantify summary[/bold]')
    print(f'- Files quantified successfully: {n_ok}')
    print(f'- Files failed: {n_fail}')
    print(f'- Output directory: {out_dir}\n')