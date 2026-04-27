'''
comMS output path utility functions
'''

# -- Import external dependencies
from pathlib import Path
from typing import Optional

# generateOutputFileStructure: returns Path to expected output directory
def generateOutputFileStructure(out_dir: Path, command: str) -> Path:
    '''
    Create and return the expected comMS output directory for a given command.
    Appends comms/results/<command>/ to out_dir if not already present.
    '''
    expected = f'comms/results/{command}'
    if not out_dir.match(expected):
        out_path = Path(out_dir, expected)
        out_path.mkdir(parents=True, exist_ok=True)
        return out_path
    return out_dir

# checkUniqueFileName: returns Path to the output file to generate
def checkUniqueFileName(
    out_dir: Path,
    command: str,
    orig_name: Optional[str] = '',
    fmt: Optional[str] = '',
) -> Path:
    '''
    Build a unique output file path for a given command, incrementing a
    counter suffix if a file with the same name already exists.
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
            if not out_path.exists():
                break
            counter += 1
    return out_path