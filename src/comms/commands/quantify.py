'''
comMS quantify functions
'''

# -- Import external dependencies
from pathlib import Path
from rich import print
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

# -- Import internal functions
from comms.utils.log import logMsg
from comms.utils.settings import config
from comms.utils.validate import validate
from comms.utils import crux as cruxutil
from comms.utils import paths as pathutil

# -- run_quantify: runs dNSAF spectral counting on all Percolator PSM files in input_dir and writes results to output
def run_quantify(input_dir: Path, database: Path, output: Path, in_pipeline: bool = False):
    if not in_pipeline:
        log = logMsg('quantify')
        log.debug('Starting quantify command')
    crux_bin, _ = validate(check_crux=True)
    logMsg.debug(f'Scanning for Percolator PSM files in: {input_dir}')
    psm_files = sorted(input_dir.glob('*.percolator.target.psms.txt'))
    if not psm_files:
        logMsg.warn(f'No Percolator PSM files found in: {input_dir}')
        print(f'[bold red]ERROR:[/bold red] No Percolator PSM files found in {input_dir}.')
        raise SystemExit(1)
    logMsg.info(f'Found {len(psm_files)} PSM file(s) — starting spectral counting')
    out_dir = pathutil.generateOutputFileStructure(output, 'quantify')
    log_path = out_dir / 'quantify.log'
    print(f'\nRunning dNSAF spectral counting on {len(psm_files)} file(s)...')
    n_ok, n_fail = 0, 0
    with logging_redirect_tqdm():
        for psm_file in tqdm(psm_files, desc='Files quantified'):
            fileroot = psm_file.name.removesuffix('.percolator.target.psms.txt')
            ok = cruxutil.spectralCounts(
                crux_bin=crux_bin,
                psm_file=psm_file,
                database=database,
                out_dir=out_dir,
                fileroot=fileroot,
                config=config,
            )
            if ok:
                n_ok += 1
            else:
                logMsg.warn(f'spectral-counts failed for: {psm_file.name}')
                n_fail += 1
    logMsg.info(f'Complete — {n_ok} succeeded, {n_fail} failed')
    if n_fail > 0:
        print(f'[bold yellow]WARNING:[/bold yellow] quantification failed for {n_fail} file(s). Check {log_path} for details.')
    print(f'\n[bold green]Quantify finished successfully - summary:[/]')
    print(f'- Files quantified successfully: {n_ok}')
    print(f'- Files failed: {n_fail}')
    print(f'- Output directory: {out_dir}\n')