'''
comMS convert functions
'''

# -- Import external dependencies
from pathlib import Path
from rich import print

# -- Import internal functions
from comms.utils.log import configureFileLogging, logMsg
from comms.utils.settings import config
from comms.utils.validate import validate
from comms.utils import trfp as trfputil
from comms.utils import paths as pathutil

# -- run_convert: converts all .RAW files in input_dir to indexed mzML and writes them to output
def run_convert(input_dir: Path, output: Path, gzip: bool, in_pipeline: bool = False):
    if not in_pipeline:
        log = logMsg('convert')
        log.debug('Starting convert command')
    _, trfp_path = validate(check_trfp=True)
    logMsg.debug(f'Scanning for .RAW files in: {input_dir}')
    raw_files = sorted(input_dir.glob('[!.]*.raw')) + sorted(input_dir.glob('[!.]*.RAW'))
    if not raw_files:
        logMsg.warn(f'No .RAW files found in: {input_dir}')
        return
    logMsg.info(f'Found {len(raw_files)} .RAW file(s) — starting conversion')
    out_dir = pathutil.generateOutputFileStructure(output, 'convert')
    log_path = out_dir / 'convert.log'
    configureFileLogging(log_path)
    print(f'\nConverting {len(raw_files)} .RAW file(s) to indexed mzML...')
    n_ok, n_fail = 0, 0
    for raw_file in raw_files:
        logMsg.info(f'Converting: {raw_file.name}')
        ok = trfputil.convertRaw(
            trfp_path=trfp_path,
            raw_file=raw_file,
            out_dir=out_dir,
            output_format=config['convert']['format'],
            gzip=gzip,
            metadata=config['convert']['metadata'],
        )
        if ok:
            n_ok += 1
        else:
            logMsg.warn(f'Conversion failed for: {raw_file.name}')
            n_fail += 1
    logMsg.info(f'Complete — {n_ok} succeeded, {n_fail} failed')
    print(f'\n[bold green]Convert finished successfully - summary:[/]')
    print(f'- Files converted successfully : {n_ok}')
    print(f'- Files failed : {n_fail}')
    print(f'- Output directory: {out_dir}\n')