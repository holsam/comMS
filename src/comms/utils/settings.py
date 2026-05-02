'''
comMS application settings and start up
'''

# -- Import external dependencies
import datetime, logging, re, tomllib
from importlib.resources import files as pkg_files
from pathlib import Path
from platformdirs import user_config_dir
from rich import print

# -- Import internal dependencies
from utils import paths as pathutils

# -- Initialise logger
lg = logging.getLogger("__name__")

# -- Define custom logger class
class logMsg:
    def __init__(self, command, msg):
        self.command = command
        self.msg = msg
        self.ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def stripRichFormatting(self, log_msg):
        return re.sub(pattern = '\\[[^A-Z]+\\]', repl='', string=log_msg)

    def debug(self):
        debug_msg = f'{self.ts} | {self.command} | [bold]DEBUG:[/] {self.msg}'
        print(debug_msg)
        lg.debug(self.stripRichFormatting(debug_msg))
    
    def info(self):
        info_msg = f'{self.ts} | {self.command} | [bold blue]INFO:[/] {self.msg}'
        print(info_msg)
        lg.info(self.stripRichFormatting(info_msg))

    def warn(self):
        warn_msg = f'{self.ts} | {self.command} | [bold yellow]WARNING:[/] {self.msg}'
        print(warn_msg)
        lg.warning(self.stripRichFormatting(warn_msg))
    
    def error(self):
        error_msg = f'{self.ts} | {self.command} | [bold red]ERROR:[/] {self.msg}'
        print(error_msg)
        lg.error(self.stripRichFormatting(error_msg))

# -- configureLogger: returns None, but set basic logging configuration
def configureLogger(level: int, out_dir: Path):
    log_file = pathutils.checkUniqueLogFile(out_dir)
    logging.basicConfig(
        filename=log_file,
        format='%(message)s',
        level=level,
    )

# -- userConfigPath: returns Path to OS-appropriate config file
def userConfigPath() -> Path:
    '''
    Returns the OS-appropriate user config path:
        Linux/macOS : ~/.config/comms/config.toml
        Windows     : %APPDATA%\\comms\\config.toml
    '''
    return Path(user_config_dir("comms"), "config.toml")

# -- loadDefaultConfig: returns dictionary of configuration settings from bundled default file
def loadDefaultConfig() -> dict:
    '''
    Load the bundled default config.toml from the installed package.
    Uses importlib.resources to avoid relative-path issues in installed packages.
    '''
    with pkg_files('comms').joinpath('config.toml').open('rb') as f:
        return tomllib.load(f)

# -- Load configuration at module import
_user_config_path = userConfigPath()
if _user_config_path.exists():
    with _user_config_path.open('rb') as _f:
        config = tomllib.load(_f)
else:
    config = loadDefaultConfig()

# -- initComms: returns None, but prints start-up message to terminal
def initComms() -> None:
    '''
    Print the comMS startup splash to the terminal.
    '''
    print(f"\n[bold]comMS[/bold] :test_tube:")
    print(f"A command line tool for comparative mass spectrometry proteomics analysis.\n")