'''
comMS index functions
'''

# -- Import external dependencies
from pathlib import Path
from rich import print

# -- Import internal functions
from comms.utils.settings import config, lg
from comms.utils import crux as cruxutil
from comms.utils import paths as pathutil

# -- run_index: builds a Tide peptide index from database and writes it to output
def run_index(database: Path, output: Path):
    lg.debug('index | Locating Crux binary...')
    bin_dir = pathutil.repoBinDir()
    crux_bin = cruxutil.findCrux(bin_dir)
    if crux_bin is None:
        print(f'[bold red]ERROR:[/bold red] Crux binary not found under {bin_dir}.')
        raise SystemExit(1)
    out_dir = pathutil.generateOutputFileStructure(output, 'index')
    log_path = out_dir / 'index.log'
    print(f'\nBuilding Tide peptide index...')
    print(f'- Database: {database}')
    print(f'- Output: {out_dir}')
    ok = cruxutil.tideIndex(
        crux_bin=crux_bin,
        database=database,
        index_dir=out_dir,
        config=config,
    )
    if not ok:
        print(f'[bold red]ERROR:[/bold red] Tide-index failed. Check {log_path} for details.')
        raise SystemExit(1)
    print(f'\n[bold green]SUCCESS:[/bold green] Peptide index written to {out_dir}\n')