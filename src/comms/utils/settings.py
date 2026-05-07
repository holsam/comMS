'''
comMS application settings and start up
'''

# -- Import external dependencies
import tomllib
from importlib.resources import files as pkg_files
from pathlib import Path
from platformdirs import user_config_dir
from rich import print

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

# -- resolveModifications: returns string of variable modifications
def resolvedModifications(cfg: dict) -> str:
    '''
    Merge the mods_spec and custom_mods entries in config and return the merged string
    '''
    index = cfg.get('index', {})
    mods = set([e.strip() for e in index.get('mods_spec', '').split(',') if e.strip()])
    custom = [e.strip() for e in index.get('custom_mods', '').split(',') if e.strip()]
    for entry in custom:
        mods.add(entry)
    return ','.join(mods)

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