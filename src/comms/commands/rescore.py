'''
comMS rescore functions
'''

# -- Import external dependencies
from pathlib import Path
from rich import print
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

# -- Import internal functions
from comms.utils.log import logMsg
from comms.utils.settings import config
from comms.utils import crux as cruxutil
from comms.utils import paths as pathutil

# -- run_rescore: rescores all Tide-search PSM files in input_dir using Percolator and writes results to output
def run_rescore(input_dir: Path, database: Path, output: Path, in_pipeline: bool = False):
    if not in_pipeline:
        log = logMsg('rescore')
        log.debug('Starting rescore command')
    logMsg.debug('Locating Crux binary')
    bin_dir = pathutil.repoBinDir()
    crux_bin = cruxutil.findCrux(bin_dir)
    if crux_bin is None:
        logMsg.error(f'Crux binary not found under: {bin_dir}')
        print(f'[bold red]ERROR:[/bold red] Crux binary not found under {bin_dir}.')
        raise SystemExit(1)
    logMsg.debug(f'Scanning for Tide-search PSM files in: {input_dir}')
    target_files = sorted(input_dir.glob('*.tide-search.target.txt'))
    if not target_files:
        logMsg.warn(f'No Tide-search target PSM files found in: {input_dir}')
        print(f'[bold red]ERROR:[/bold red] No Tide-search target PSM files found in {input_dir}.')
        raise SystemExit(1)
    logMsg.info(f'Found {len(target_files)} PSM file(s) — starting rescoring')
    out_dir = pathutil.generateOutputFileStructure(output, 'rescore')
    log_path = out_dir / 'rescore.log'
    print(f'\nRescoring {len(target_files)} PSM file(s) with Percolator...')
    n_ok, n_fail = 0, 0
    with logging_redirect_tqdm():
        for target_file in tqdm(target_files, desc='Files rescored'):
            fileroot = target_file.name.removesuffix('.tide-search.target.txt')
            ok = cruxutil.percolator(
                crux_bin=crux_bin,
                target_psm_file=target_file,
                database=database,
                out_dir=out_dir,
                fileroot=fileroot,
                config=config,
            )
            if ok:
                n_ok += 1
            else:
                logMsg.warn(f'Percolator failed for: {target_file.name}')
                n_fail += 1
    logMsg.info(f'Complete — {n_ok} succeeded, {n_fail} failed')
    if n_fail > 0:
        print(f'[bold yellow]WARNING:[/bold yellow] rescoring failed for {n_fail} file(s). Check {log_path} for details.')
    print(f'\n[bold green]Rescore finished successfully - summary:[/]')
    print(f'- Files rescored successfully: {n_ok}')
    print(f'- Files failed: {n_fail}')
    print(f'- Output directory: {out_dir}\n')