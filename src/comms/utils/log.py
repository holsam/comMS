'''
Shared utility functions: logging
'''
# -- Import external dependencies
import atexit, logging, shutil, sys, tempfile, time
from pathlib import Path
from rich.console import Console, ConsoleRenderable
from rich.logging import RichHandler
from rich.prompt import Prompt
from rich.text import Text

# -- Define level colours for RichHandler
_LEVEL_COLOURS: dict[str, str] = {
    'DEBUG':    'color(67)',
    'PROGRESS': 'color(75)',
    'INFO':     'color(33)',
    'INPUT':    'color(28)',
    'WARNING':  'color(178)',
    'ERROR':    'color(160)',
    'CRITICAL': 'color(124)',
}

# -- Register custom PROGRESS logging level
PROGRESS = 15
logging.addLevelName(PROGRESS, 'PROGRESS')

def _progress(self, message, *args, **kwargs):
    if self.isEnabledFor(PROGRESS):
        self._log(PROGRESS, message, args, **kwargs)

logging.Logger.progress = _progress

# -- Register custom INPUT logging level
INPUT = 45
logging.addLevelName(INPUT, 'INPUT')

def _input(self, message, *args, **kwargs):
    if self.isEnabledFor(INPUT):
        self._log(INPUT, message, args, **kwargs)

logging.Logger.input = _input


# -- Define custom RichHandler subclass (CommsRichHandler) to allow custom formatting
class CommsRichHandler(RichHandler):
    def emit(self, record: logging.LogRecord) -> None:
        log_state._emitted = True
        if getattr(record, '_suppress_console', False):
            return
        super().emit(record)
    def render_message(self, record: logging.LogRecord, message: str) -> 'ConsoleRenderable':
        level_colour = _LEVEL_COLOURS.get(record.levelname, 'white')
        markup = (
            f"[dim]{self.formatter.formatTime(record, self.formatter.datefmt)}[/dim] | "
            f"[bold]{record.name}[/bold] | "
            f"[bold {level_colour}]{record.levelname}[/] | [white]{message}[/]"
        )
        return Text.from_markup(markup)

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
    def progress(cls, msg:str):
        if cls._instance:
            cls._instance.logger.progress(msg)
    @classmethod
    def info(cls, msg: str):
        if cls._instance:
            cls._instance.logger.info(msg)
    @classmethod
    def input(cls, msg: str, **prompt_kwargs) -> str | None:
        if not cls._instance:
            return None
        logger = cls._instance.logger
        if not logger.isEnabledFor(INPUT):
            return None
        interactive = sys.stdin.isatty()
        if interactive:
            level_colour = _LEVEL_COLOURS.get('INPUT', 'white')
            console = Console(stderr=True)
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            styled_prompt = (
                f"[dim]{timestamp}[/dim] | "
                f"[bold]{logger.name}[/bold] | "
                f"[bold {level_colour}]INPUT[/] | [white]{msg}[/]"
            )
            prompt_obj = Prompt(
                styled_prompt,
                console=console,
                choices=prompt_kwargs.get('choices'),
                show_default=prompt_kwargs.get('show_default', True),
                show_choices=prompt_kwargs.get('show_choices', True),
            )
            prompt_obj.case_sensitive = prompt_kwargs.get('case_sensitive', True)
            default = prompt_kwargs.get('default', ...)
            answer = prompt_obj(default=default, stream=prompt_kwargs.get('stream'))
            # Work out how many terminal rows the prompt (and the typed answer, if echoed) actually occupied, so wrapped prompts get fully erased rather than leaving fragments behind
            rendered = prompt_obj.make_prompt(default)
            total_len = len(rendered.plain) + len(str(answer))
            width = console.width or 80
            rows = max(1, -(-total_len // width))  # ceil division
            for _ in range(rows):
                console.file.write("\x1b[1A\x1b[2K")
            console.file.write("\r")
            console.file.flush()
        else:
            answer = prompt_kwargs.get('default')
        logger.input(f"{msg}: {answer}")
        return answer
    @classmethod
    def warn(cls, msg: str):
        if cls._instance:
            cls._instance.logger.warning(msg)
    @classmethod
    def error(cls, msg: str):
        if cls._instance:
            cls._instance.logger.error(msg)

# -- Define custom class LogState to track log level and temp log file
class LogState:
    log_level: int = logging.INFO
    _temp_log_file: tempfile.NamedTemporaryFile | None = None
    _temp_log_path: Path | None = None
    _file_handler: logging.FileHandler | None = None
    _emitted: bool = False
    _atexit_registered: bool = False
    _pipeline_log_paths: list[Path] | None = None

# -- Define custom logging.Formatter subclas (PlainFormatter) to strip Rich markup before writing to file
class PlainFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record = logging.makeLogRecord(record.__dict__)
        try:
            record.msg = Text.from_markup(str(record.msg)).plain
        except Exception:
            pass  # leave message as-is if markup parsing fails
        return super().format(record)

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

# -- configureStreamLogging: attach a RichHandler stream handler and temp file handler
def configureStreamLogging():
    logger = logging.getLogger()
    logger.setLevel(log_state.log_level)
    if any(isinstance(h, RichHandler) for h in logger.handlers):
        return
    handler = CommsRichHandler(
        level=log_state.log_level,
        console=Console(stderr=True),
        rich_tracebacks=True,
        markup=True,
        show_path=False,
        show_time=False,
        show_level=False,
    )
    # Formatter is only used for formatTime
    handler.setFormatter(logging.Formatter(datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(handler)
    _attachTempFileHandler()
    if not log_state._atexit_registered:
        atexit.register(_emitTrailingNewline)
        log_state._atexit_registered = True

# -- configureFileLogging: flush temp log to its final location under out_dir
def configureFileLogging(out_dir: Path):
    logger = logging.getLogger()
    # Remove the temp file handler
    if log_state._file_handler is not None:
        logger.removeHandler(log_state._file_handler)
        log_state._file_handler.close()
        log_state._file_handler = None
    # Copy temp log contents to the final path
    final_path = checkUniqueLogFile(out_dir)
    final_path.parent.mkdir(parents=True, exist_ok=True)
    if log_state._temp_log_path is not None and log_state._temp_log_path.exists():
        shutil.copy2(log_state._temp_log_path, final_path)
    # Attach a new file handler pointed at the final path
    handler = logging.FileHandler(final_path, mode='a')
    handler.setLevel(log_state.log_level)
    handler.setFormatter(_plainFormatter())
    logger.addHandler(handler)
    log_state._file_handler = handler
    _removeTempLog()
    # Track this log file if pipeline is aggregating logs
    if log_state._pipeline_log_paths is not None:
        log_state._pipeline_log_paths.append(final_path)

# -- startPipelineLogging: begin tracking per-command log files for later aggregation into pipeline.log
def startPipelineLogging():
    log_state._pipeline_log_paths = []

# -- concatenatePipelineLog: concatenate per-command log files into pipeline.log
def concatenatePipelineLog(out_path: Path) -> Path | None:
    paths = log_state._pipeline_log_paths or []
    log_state._pipeline_log_paths = None  # stop tracking regardless of outcome
    if not paths:
        return None
    final_path = checkUniqueLogFile(out_path)
    final_path.parent.mkdir(parents=True, exist_ok=True)
    with open(final_path, 'w') as pipeline_log:
        for path in paths:
            section = path.parent.name  # e.g. 'convert', 'index', 'search'
            pipeline_log.write(f"\n{'=' * 80}\n# {section}  ({path})\n{'=' * 80}\n\n")
            if path.exists():
                pipeline_log.write(path.read_text())
            else:
                pipeline_log.write(f'[log file missing: {path}]\n')
    return final_path

# -- _plainFormatter: internal helper to format log messages 
def _plainFormatter() -> PlainFormatter:
    return PlainFormatter(
        fmt="%(asctime)s | %(name)s | %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

# -- _attachTempFileHandler: internal helper to attach a temporary file as a file handler until actual log file is known from output directory
def _attachTempFileHandler():
    if log_state._file_handler is not None:
        return
    tmp = tempfile.NamedTemporaryFile(prefix='comms_', suffix='.log', delete=False)
    log_state._temp_log_file = tmp
    log_state._temp_log_path = Path(tmp.name)
    handler = logging.FileHandler(tmp.name, mode='a')
    handler.setLevel(log_state.log_level)
    handler.setFormatter(_plainFormatter())
    logging.getLogger().addHandler(handler)
    log_state._file_handler = handler

# -- _removeTempLog: internal helper to remove temporary log file once
def _removeTempLog():
    try:
        if log_state._temp_log_path and log_state._temp_log_path.exists():
            log_state._temp_log_path.unlink()
    except OSError:
        pass
    log_state._temp_log_file = None
    log_state._temp_log_path = None

# -- _emitTrailingNewline: internal helper to print a blank line (only in interactive terminals)
def _emitTrailingNewline() -> None:
    if log_state._emitted and sys.stderr.isatty():
        Console(stderr=True).print()

# -- Initialise state
log_state = LogState()