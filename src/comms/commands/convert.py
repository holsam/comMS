'''
comMS convert functions
'''

# -- Import external dependencies
from pathlib import Path
from rich import print

# -- Import internal functions
from comms.utils.log import configureFileLogging, logMsg
from comms.utils.settings import ExperimentContext
from comms.utils.validate import validate
from comms.utils import trfp as trfputil
from comms.utils import paths as pathutil

# -- run_convert: converts all .RAW files in input_dir to indexed mzML and writes them to output
def run_convert(input_dir: Path, ctx: ExperimentContext, gzip: bool | None = None, in_pipeline: bool = False):
    if not in_pipeline:
        logMsg('convert')
    logMsg.debug('Started command: convert')
    gzip = ctx.config['convert']['gzip'] if gzip is None else gzip
    _, trfp_path = validate(check_trfp=True, bin_dir=ctx.bin_dir)
    logMsg.debug(f'Scanning {input_dir} for .RAW files')
    raw_files = sorted(input_dir.glob('[!.]*.raw')) + sorted(input_dir.glob('[!.]*.RAW'))
    if not raw_files:
        logMsg.warn(f'No .RAW files found in {input_dir}')
        return
    logMsg.info(f'Converting {len(raw_files)} .RAW file(s) to indexed mzML file(s)')
    out_dir = pathutil.generateOutputFileStructure(ctx.root, 'convert')
    logMsg.debug(f'Output directory: {out_dir}')
    log_path = out_dir / 'convert.log'
    configureFileLogging(log_path)
    logMsg.debug(f'Output log file: {log_path}')
    n_ok, n_fail = 0, 0
    for raw_file in raw_files:
        logMsg.progress(f'Converting {raw_file.name}')
        ok = trfputil.convertRaw(
            trfp_path=trfp_path,
            raw_file=raw_file,
            out_dir=out_dir,
            output_format=ctx.config['convert']['format'],
            gzip=gzip,
            metadata=ctx.config['convert']['metadata'],
        )
        if ok:
            n_ok += 1
        else:
            logMsg.warn(f'Conversion failed for {raw_file.name}')
            n_fail += 1
    logMsg.info(f'Conversion complete: {n_ok} succeeded, {n_fail} failed')
    logMsg.debug(f'Finished command: convert')