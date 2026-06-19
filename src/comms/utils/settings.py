'''
comMS application settings and start up
'''

# -- Import external dependencies
import tomllib
from importlib.resources import files as pkg_files
from pathlib import Path
from platformdirs import user_config_dir
from rich import print
from typing import Optional

# Import internal classes/functions
from comms.utils.log import logMsg

# -- globalConfigPath: returns Path to OS-appropriate config file
def globalConfigPath() -> Path:
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
    fixed = set([e.strip() for e in index.get('fixed_mods', '').split(',') if e.strip()]) 
    custom = [e.strip() for e in index.get('custom_mods', '').split(',') if e.strip()]
    for entry in fixed:
        mods.add(entry)
    for entry in custom:
        mods.add(entry)
    return ','.join(mods)

# -- _loadTomlFile: returns dict parsed from a TOML file on disk
def _loadTomlFile(path: Path) -> dict:
    with path.open('rb') as f:
        return tomllib.load(f)

# -- resolveConfig: returns (config, source)
def resolveConfig(comms_dir: Optional[Path] = None) -> tuple[dict, str]:
    '''
    Resolve the active config using priority: local > global > default
    '''
    if comms_dir is not None:
        local_path = comms_dir / 'config.toml'
        if local_path.exists():
            logMsg.debug(f'Using local config: {local_path}')
            return _loadTomlFile(local_path), f'local ({local_path})'
    global_path = globalConfigPath()
    if global_path.exists():
        logMsg.debug(f'Using global config: {global_path}')
        return _loadTomlFile(global_path), f'global ({global_path})'
    logMsg.debug('Using bundled default config')
    return loadDefaultConfig(), 'bundled defaults'

# -- initComms: returns None, but prints start-up message to terminal
def initComms() -> None:
    '''
    Print the comMS startup splash to the terminal.
    '''
    print(f"\n[bold]comMS[/bold] :test_tube:")
    print(f"A command line tool for comparative mass spectrometry proteomics analysis.\n")