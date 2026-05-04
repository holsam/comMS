'''
comMS wrapper around ThermoRawFileParser
'''

# -- Import external dependencies
import platform, shutil, subprocess
from pathlib import Path
from typing import Optional

# -- Import internal functions
from comms.utils.log import logMsg

# -- findTRFP: returns a Path to ThermoRawFileParser.exe under bin_dir, or None if not found
def findTRFP(bin_dir: Path) -> Optional[Path]:
    logMsg.debug(f'Searching for ThermoRawFileParser under: {bin_dir}')
    matches = list(bin_dir.glob('*/ThermoRawFileParser.exe'))
    if not matches:
        logMsg.warn(f'No ThermoRawFileParser binary found under: {bin_dir}')
        return None
    result = sorted(matches)[-1]
    logMsg.debug(f'ThermoRawFileParser found: {result}')
    return result

# -- convertRaw: returns True on successful conversion of a .RAW file to indexed mzML or False on failure
def convertRaw(
    exe_path: Path,
    raw_file: Path,
    out_dir: Path,
    output_format: int = 2,
    gzip: bool = True,
    metadata: int = 0,
    log_path: Optional[Path] = None,
) -> bool:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [str(exe_path),
           '--input', str(raw_file),
           '--output', str(out_dir),
           '--format', str(output_format),
           '--metadata', str(metadata)]
    if gzip:
        cmd.append('--gzip')
    is_windows = platform.system() == 'Windows'
    if not is_windows:
        mono = shutil.which('mono')
        if mono is None:
            logMsg.error('Mono not found — required to run ThermoRawFileParser on non-Windows systems')
            return False
        cmd = [mono] + cmd
    logMsg.debug(f'Running: {" ".join(cmd)}')
    log_fh = open(log_path, 'a') if log_path else subprocess.DEVNULL
    try:
        result = subprocess.run(cmd, stdout=log_fh, stderr=log_fh, check=False)
        if result.returncode != 0:
            logMsg.warn(f'ThermoRawFileParser exited with non-zero return code {result.returncode} for {raw_file.name}')
            return False
        return True
    except Exception as e:
        logMsg.error(f'Unexpected error converting {raw_file.name}: {e}')
        return False
    finally:
        if log_path:
            log_fh.close()