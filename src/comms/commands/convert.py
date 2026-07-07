'''
comMS convert functions
'''

# -- Import external dependencies
from pathlib import Path
from rich import print

# -- Import internal functions
from comms.utils.log import configureFileLogging, logMsg
from comms.utils.context import ExperimentContext, resolve_data_files
from comms.utils.validate import validate
from comms.utils import trfp as trfputil
from comms.utils import paths as pathutil

# -- run_convert: converts all .RAW files in input_dir to indexed mzML and writes them to output
def run_convert(data_files, ctx: ExperimentContext, gzip: bool | None = None, in_pipeline: bool = False):
    if not in_pipeline:
        logMsg('convert')
    logMsg.debug('Started command: convert')
    gzip = ctx.config['convert']['gzip'] if gzip is None else gzip
    _, trfp_path = validate(check_trfp=True, bin_dir=ctx.bin_dir)
    data_files = resolve_data_files(ctx, data_files)
    raw_files = [f for f in data_files if f.suffix.lower() == '.raw']
    if not raw_files:
        logMsg.warn('No .RAW files among the resolved data files')
        return
    try:
        from comms.utils.samples import loadSampleSheet
        samples = loadSampleSheet(ctx.sample_sheet)
        raw_to_id = dict(zip(samples['raw_file'], samples['sample_id']))
    except Exception as e:
        logMsg.debug(f'Could not load sample sheet: {e}')
        samples = None
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
            metadata=ctx.config['convert']['metadata'],
        )
        if ok:
            n_ok += 1
        else:
            logMsg.warn(f'Conversion failed for {raw_file.name}')
            n_fail += 1
    # If sample sheet provided, rename files
    if samples is not None:
        for file in out_dir.glob('[!.]*'):
            try:
                # Rename sample files
                sample_id = raw_to_id.get(f'{file.stem}.raw')
                if sample_id is not None:
                    suffixes = ''.join(file.suffixes)
                    file.rename(file.with_name(f'{sample_id}{suffixes}'))
                # Rename metadata files
                else:
                    metadata_sample = raw_to_id.get(f'{file.stem.removesuffix('-metadata')}.raw')
                    if metadata_sample is not None:
                        suffixes = ''.join('-metadata', file.suffixes)
                        file.rename(file.with_name(f'{metadata_sample}{suffixes}'))
            except:
                continue
    # If --gzip was provided, gzip TRFP output
    if gzip:
        import gzip, os, shutil
        # Loop through each mzML file in directory
        for file in out_dir.glob('[!.]*.mzML'):
            # Create gzipped file
            with open(file, 'rb') as f_in:
                with gzip.open(Path(f'{file}.gz'), 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            # Delete mzML file
            os.remove(file)
    logMsg.info(f'Conversion complete: {n_ok} succeeded, {n_fail} failed')
    logMsg.debug(f'Finished command: convert')