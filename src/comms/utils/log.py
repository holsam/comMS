'''
Shared utility functions: logging
'''
# -- Import external dependencies
import logging, shutil
from pathlib import Path

# -- Define custom logger class
class logMsg:
    _instance: 'logMsg | None' = None
    def __init__(self, command: str):
        self.logger = logging.getLogger(command)
        logMsg._instance = self
    @classmethod
    def debug(cls, msg: str):
        if cls._instance:
            cls._instance.logger.debug(msg)
    @classmethod
    def info(cls, msg: str):
        if cls._instance:
            cls._instance.logger.info(msg)
    @classmethod
    def warn(cls, msg: str):
        if cls._instance:
            cls._instance.logger.warning(msg)
    @classmethod
    def error(cls, msg: str):
        if cls._instance:
            cls._instance.logger.error(msg)

# -- Define custom class LogState to define log level
class LogState:
    log_level: int = logging.INFO

# -- checkUniqueLogFile: returns string corresponding to path to uniquely-named log file
def checkUniqueLogFile(
    log_file: Path,
) -> Path:
    '''
    Build a unique output file path for the comms log file, incrementing a counter suffix if a file with the same name already exists.
    '''
    stem = log_file.stem
    suffix = log_file.suffix
    dir = log_file.parent
    counter = 0
    while log_file.exists():
        counter += 1
        log_file = dir / f'{stem}-{counter}{suffix}'
    return(log_file)

def configureStreamLogging():
    """Attach a stream handler to the root logger at the current log level."""
    logger = logging.getLogger()
    logger.setLevel(log_state.log_level)
    # Avoid adding duplicate handlers on repeated calls
    if any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
           for h in logger.handlers):
        return
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(name)s | %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler = logging.StreamHandler()
    handler.setLevel(log_state.log_level)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def configureFileLogging(out_dir: Path):
    """Attach a file handler once out_dir is known."""
    logger = logging.getLogger()
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(name)s | %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    log_file = checkUniqueLogFile(out_dir=out_dir)
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_file)
    handler.setLevel(log_state.log_level)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# -- Initialise state
log_state = LogState()