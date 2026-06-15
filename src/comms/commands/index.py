'''
comMS index functions
'''

# -- Import external dependencies
from pathlib import Path
from rich import print

# -- Import internal functions
from comms.utils.log import configureFileLogging, logMsg
from comms.utils.settings import config
from comms.utils.validate import validate
from comms.utils import crux as cruxutil
from comms.utils import paths as pathutil

# -- run_index: builds a Tide peptide index from database and writes it to output
def run_index(database: Path, output: Path, in_pipeline: bool = False):
    if not in_pipeline:
        logMsg('index')
    logMsg.debug('Started command: index')
    crux_bin, _ = validate(check_crux=True)
    logMsg.info(f'Indexing database {database.name}')
    out_dir = pathutil.generateOutputFileStructure(output, 'index')
    logMsg.debug(f'Output directory: {out_dir}')
    log_path = out_dir / 'index.log'
    configureFileLogging(log_path)
    logMsg.debug(f'Output log file: {log_path}')
    logMsg.progress(f'Building Tide peptide index')
    ok = cruxutil.tideIndex(
        crux_bin=crux_bin,
        database=database,
        index_dir=out_dir,
        config=config,
    )
    if not ok:
        logMsg.error(f'tide-index failed, see {log_path}')
        raise SystemExit(1)
    logMsg.info(f'Indexing complete: peptide index saved to {out_dir}')
    logMsg.debug(f'Finished command: index')