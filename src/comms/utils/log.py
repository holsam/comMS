'''
Shared utility functions: logging
'''
# -- Import external dependencies
import logging
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
    def info(cls, msg):
        if cls._instance:
            cls._instance.logger.info(msg)
    @classmethod
    def warn(cls, msg):
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
    out_dir: Path,
) -> str:
    '''
    Build a unique output file path for the comms log file, incrementing a counter suffix if a file with the same name already exists.
    '''
    out_path = Path(out_dir, "comms/comms.log")
    if out_path.exists():
        stem = out_path.stem
        suffix = out_path.suffix
        counter = 1
        while True:
            out_path = Path(out_dir, f'{stem}-{counter}{suffix}')
            if not out_path.exists():
                break
            counter +=1
        return str(out_path)

# -- configureLogger: returns None but sets up logging configuration
def configureLogger(out_dir: Path):
    logger = logging.getLogger()
    logger.setLevel(log_state.log_level)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(name)s | %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    # Handler for stdout
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(log_state.log_level)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    # Handler for log file
    log_file = checkUniqueLogFile(out_dir=out_dir)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_state.log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

# -- Initialise state
log_state = LogState()