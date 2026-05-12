'''
comMS output path utility functions
'''

# -- Import external dependencies
import os
from pathlib import Path
from typing import Optional

# -- Import internal dependencies
from comms.utils.log import logMsg

# repoBinDir: returns Path to bin/ directory in repo root
def repoBinDir() -> Path:
    '''
    Returns the repo-root bin/ directory resolved from COMMS_BIN_DIR environment variable if set otherwise walks back up repo
    '''
    env_override = os.environ.get('COMMS_BIN_DIR')
    if env_override:
        return Path(env_override)
    return Path(__file__).parents[3] / 'bin'

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
        logMsg.debug(f'Output directory created: {base}')
        return base
    # Increment until we find an unused directory
    counter = 1
    while True:
        candidate = Path(out_dir, f'comms/results/{command}-{counter}')
        logMsg.debug(f'Output directory already exists, incrementing: {candidate}')
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
            logMsg.debug(f'Output filename already exists, incrementing: {out_path}')
            if not out_path.exists():
                break
            counter += 1
    return out_path