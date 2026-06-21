'''
comMS wrapper around ThermoRawFileParser
'''

# -- Import external dependencies
import platform, shutil, subprocess
from pathlib import Path
from rich.live import Live
from rich.text import Text
from typing import Optional

# -- Import internal functions
from comms.utils.log import logMsg
from comms.utils.validate import _get_trfp_version

# -- findTRFP: returns a Path to ThermoRawFileParser.exe under bin_dir, or None if not found
def findTRFP(bin_dir: Path) -> Optional[Path]:
    logMsg.debug(f'Searching for ThermoRawFileParser in {bin_dir}')
    matches = list(bin_dir.glob('*/ThermoRawFileParser.exe'))
    matches += list(bin_dir.glob('*/ThermoRawFileParser'))
    if not matches:
        logMsg.debug(f'No ThermoRawFileParser binary in {bin_dir}')
        return None
    result = sorted(matches)[-1]
    logMsg.debug(f'Selected ThermoRawFileParser: {result}')
    return result

# -- convertRaw: returns True on successful conversion of a .RAW file to indexed mzML or False on failure
def convertRaw(
    trfp_path: Path,
    raw_file: Path,
    out_file: Path,
    output_format: int = 2,
    gzip: bool = True,
    metadata: int = 0,
    log_path: Optional[Path] = None,
) -> bool:
    out_file.mkdir(parents=True, exist_ok=True)
    # Construct base command
    cmd = [str(trfp_path),
           '--input', str(raw_file),
           '--output', str(out_file),
           '--format', str(output_format),
           '--metadata', str(metadata)]
    # Check if Mono is required
    if (_get_trfp_version(trfp_path) < (2, 0, 0, 0)) and not (platform.system() == 'Windows'):
        mono = shutil.which('mono')
        if mono is None:
            logMsg.warn('Mono not found, but is reqired by ThermoRawFileParser on  non-Windows systems')
            return False
        cmd = [mono] + cmd
    log_fh = open(log_path, 'a') if log_path else subprocess.DEVNULL
    try:
        logMsg.debug(f'TFRP converting {" ".join(cmd)}')
        stderr_lines = []
        with subprocess.Popen(
            cmd,
            stderr=subprocess.PIPE,
            stdout=log_fh,
            text=True
        ) as proc:
            with Live('', refresh_per_second=10, transient=True) as live:
                for line in proc.stderr:
                    line = line.rstrip()
                    if line:
                        stderr_lines.append(line)
                        live.update(Text(line, style='dim'))
        if proc.returncode != 0:
            logMsg.warn(f'ThermoRawFileParser exited {proc.returncode} for {raw_file.name}')
            return False
    except Exception as e:
        logMsg.error(f'Unexpected error converting {raw_file.name}: {e}')
        return False
    finally:
        if log_path:
            log_fh.close()
    # If gzip was provided, gzip TRFP output
    if gzip:
        import gzip
        out_match = list(out_file.parent.glob(f'{out_file.stem}.*'))
        if len(out_match) > 1:
            logMsg.warn(f'Could not compress ThermoRawFileParser output')
        trfp_out = out_match[0]
        with open(trfp_out, 'rb') as f_in:
            with gzip.open(Path(f'{trfp_out}.gz'), 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
    return True