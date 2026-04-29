'''
comMS convert functions
'''

# -- Import external dependencies
from pathlib import Path
from rich import print

# -- Import internal functions
from comms.utils.settings import config, lg
from comms.utils import trfp as trfputil
from comms.utils import paths as pathutil

# -- run_convert: converts all .RAW files in input_dir to indexed mzML and writes them to output
def run_convert(input_dir: Path, output: Path, gzip: bool):
    lg.debug('convert | Locating ThermoRawFileParser...')
    import shutil
    bin_dir = pathutil.repoBinDir()
    exe_path = trfputil.findTRFP(bin_dir)
    if exe_path is None:
        print(f'[bold red]ERROR:[/bold red] ThermoRawFileParser.exe not found under {bin_dir}.')
        raise SystemExit(1)
    lg.debug('convert | Scanning for .RAW files...')
    raw_files = sorted(input_dir.glob('*.raw')) + sorted(input_dir.glob('*.RAW'))
    if not raw_files:
        print(f'[bold yellow]WARNING:[/bold yellow] No .RAW files found in {input_dir}.')
        return
    out_dir = pathutil.generateOutputFileStructure(output, 'convert')
    log_path = out_dir / 'convert.log'
    print(f'\nConverting {len(raw_files)} .RAW file(s) to indexed mzML...')
    n_ok, n_fail = 0, 0
    for raw_file in raw_files:
        lg.info(f'convert | Converting {raw_file.name}...')
        ok = trfputil.convertRaw(
            exe_path=exe_path,
            raw_file=raw_file,
            out_dir=out_dir,
            output_format=config['convert']['format'],
            gzip=gzip,
            metadata=config['convert']['metadata'],
            log_path=log_path,
        )
        if ok:
            n_ok += 1
        else:
            lg.warning(f'convert | Conversion failed for {raw_file.name}.')
            n_fail += 1
    print(f'\n[bold]Convert summary[/bold]')
    print(f'- Files converted successfully : {n_ok}')
    print(f'- Files failed : {n_fail}')
    print(f'- Output directory: {out_dir}\n')