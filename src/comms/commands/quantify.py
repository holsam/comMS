'''
comMS quantify functions
'''

# -- Import external dependencies
from pathlib import Path
from rich import print
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

# -- Import internal functions
from comms.utils.log import configureFileLogging, logMsg
from comms.utils.context import ExperimentContext, resolve_database, resolve_results_input
from comms.utils.validate import validate
from comms.utils import crux as cruxutil
from comms.utils import paths as pathutil

# -- run_quantify: runs dNSAF spectral counting on assign-confidence PSM files (discovering single/multi-species results) and writes results to output
def run_quantify(input_dir, database, ctx: ExperimentContext, in_pipeline: bool = False):
    if not in_pipeline:
        logMsg('quantify')
    logMsg.debug('Started command: quantify')
    crux_bin, _ = validate(check_crux=True, bin_dir=ctx.bin_dir)
    input_dir = resolve_results_input(ctx, 'rescore', input_dir)
    database = resolve_database(ctx, database)
    # Discover both layouts: per-organism subdirectories and flat
    logMsg.debug(f'Scanning {input_dir} for assign-confidence PSMs')
    psm_files = sorted(input_dir.glob('[!.]*/*.assign-confidence.target.txt'))  # multi (per-organism)
    psm_files += sorted(input_dir.glob('[!.]*.assign-confidence.target.txt'))    # single (flat)

    if not psm_files:
        logMsg.error(f'No assign-confidence PSM files found in {input_dir}')
        raise SystemExit(1)
    logMsg.info(f'Quantifying {len(psm_files)} PSM file(s)')
    out_dir = pathutil.generateOutputFileStructure(ctx.root, 'quantify')
    logMsg.debug(f'Output directory: {out_dir}')
    log_path = out_dir / 'quantify.log'
    configureFileLogging(log_path)
    logMsg.debug(f'Output log file: {log_path}')
    n_ok, n_fail = 0, 0
    with logging_redirect_tqdm():
        for psm_file in tqdm(psm_files, desc='Files quantified'):
            logMsg.progress(f'Quantifying {psm_file.name}')
            fileroot = psm_file.name.removesuffix('.assign-confidence.target.txt')
            ok = cruxutil.spectralCounts(
                crux_bin=crux_bin,
                psm_file=psm_file,
                database=database,
                out_dir=out_dir,
                fileroot=fileroot,
                config=ctx.config,
            )
            if ok:
                n_ok += 1
            else:
                logMsg.warn(f'Quantification failed for {psm_file.name}')
                n_fail += 1
    logMsg.info(f'Quantification complete: {n_ok} succeeded, {n_fail} failed')
    logMsg.debug('Finished command: quantify')