'''
comMS output path utility functions
'''

# -- Import external dependencies
import os
from pathlib import Path
from typing import Optional

# -- Import internal dependencies
from comms.utils.log import logMsg

# repoBinDir: returns Path to the bin/ directory holding external binaries
def repoBinDir(experiment_bin_dir: Optional[Path] = None) -> Path:
    '''
    Resolve the bin/ directory, in priority order:
      1. an explicit experiment_bin_dir (from experiment.toml)
      2. the COMMS_BIN_DIR environment variable
      3. the repo-root bin/ directory (development)
    '''
    if experiment_bin_dir is not None:
        logMsg.debug(f'Using experiment bin directory: {experiment_bin_dir}')
        return experiment_bin_dir
    env_override = os.environ.get('COMMS_BIN_DIR')
    bin_dir = Path(env_override) if env_override else Path(__file__).parents[3] / 'bin'
    logMsg.debug(f'Using bin directory: {bin_dir}')
    return bin_dir

# generateOutputFileStructure: returns Path to expected output directory
def generateOutputFileStructure(out_dir: Path, command: str) -> Path:
    '''
    Create and return the expected comMS output directory for a given command.
    Appends comms/results/<command>/ to out_dir if not already present.
    '''
    expected = f'comms/results/{command}'
    if out_dir.match(expected):
        return out_dir
    base = Path(out_dir, expected)
    if not base.exists():
        base.mkdir(parents=True, exist_ok=True)
        logMsg.debug(f'Created output directory: {base}')
        return base
    # Increment until we find an unused directory
    counter = 1
    while True:
        candidate = Path(out_dir, f'comms/results/{command}-{counter}')
        logMsg.debug(f'Output directory exists, trying {candidate}')
        if not candidate.exists():
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        counter += 1


# checkUniqueFileName: returns Path to the output file to generate
def checkUniqueFileName(
    out_dir: Path,
    command: str,
    orig_name: Optional[str] = '',
    fmt: Optional[str] = '',
) -> Path:
    '''
    Build a unique output file path for a given command, incrementing a counter suffix if a file with the same name already exists.
    '''
    naming = {
        'convert': f'{orig_name}.mzML.gz',
        'index': 'comms-index',
        'search': f'{orig_name}.tide-search.target.txt',
        'rescore': f'{orig_name}.percolator.psms.txt',
        'quantify': f'{orig_name}.spectral-counts.txt',
        'report': f'comms-report.{fmt}' if fmt else 'comms-report.html',
    }
    base_name = naming.get(command, f'comms-{command}-output')
    out_path = Path(out_dir, base_name)
    if out_path.exists():
        stem = out_path.stem
        suffix = out_path.suffix
        counter = 1
        while True:
            out_path = Path(out_dir, f'{stem}-{counter}{suffix}')
            logMsg.debug(f'Output filename exists, trying {out_path}')
            if not out_path.exists():
                break
            counter += 1
    return out_path