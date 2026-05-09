'''
comMS index functions
'''

# -- Import external dependencies
from pathlib import Path
from rich import print

# -- Import internal functions
from comms.utils.log import logMsg
from comms.utils.settings import config
from comms.utils.validate import validate
from comms.utils import crux as cruxutil
from comms.utils import paths as pathutil

# -- run_index: builds a Tide peptide index from database and writes it to output
def run_index(database: Path, output: Path, in_pipeline: bool = False):
    if not in_pipeline:
        log = logMsg('index')
        log.debug('Starting index command')
    crux_bin, _ = validate(check_crux=True)
    logMsg.info(f'Building Tide peptide index from: {database.name}')
    out_dir = pathutil.generateOutputFileStructure(output, 'index')
    log_path = out_dir / 'index.log'
    ok = cruxutil.tideIndex(
        crux_bin=crux_bin,
        database=database,
        index_dir=out_dir,
        config=config,
    )
    if not ok:
        logMsg.error(f'tide-index failed — see: {log_path}')
        raise SystemExit(1)
    logMsg.info(f'Peptide index written to: {out_dir}')
    print(f'\n[bold green]Index finished successfully - summary:[/]')
    print(f'- Source database: {database}')
    print(f'- Output: {out_dir}')
