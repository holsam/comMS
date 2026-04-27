'''
comMS config functions
'''

# -- Import external dependencies
import tomllib, tomli_w, typer
from pathlib import Path
from rich import print
from rich.console import Console
from rich.table import Table
from typing import Annotated

# -- Import internal functions
from comms.utils.settings import loadDefaultConfig, userConfigPath

# -- config_init: creates a user config file with default settings in the OS config directory
def config_init():
    print()
    config_path = userConfigPath()
    if not _configCheck(config_path, exists=False):
        raise typer.Exit(1)
    try:
        defaults = loadDefaultConfig()
        _writeConfig(defaults)
        print(f'[bold green]SUCCESS:[/bold green] User config written to [cyan]{config_path}[/cyan]\n')
    except Exception as e:
        print(f'[bold red]ERROR:[/bold red] Could not write config: {e}\n')
        raise typer.Exit(1)

# -- config_exists: reports whether a user config file exists and prints its path
def config_exists():
    print()
    config_path = userConfigPath()
    if config_path.exists():
        print(f'[bold green]SUCCESS:[/bold green] User config found at [cyan]{config_path}[/cyan]\n')
    else:
        print(f'[bold yellow]WARNING:[/bold yellow] No user config at [cyan]{config_path}[/cyan]\nRun [bold]comms config init[/bold] to create one.\n')
        raise typer.Exit(1)

# -- config_list: prints current config values, highlighting differences from bundled defaults
def config_list():
    config_path = userConfigPath()
    default_config = _flatten(loadDefaultConfig())
    if _configCheck(config_path, exists=True):
        print(f'[bold blue]Current config:[/bold blue] [cyan]{config_path}[/cyan]\n')
        current_config = _flatten(_loadUserConfig())
    else:
        print(f'[bold blue]Current config:[/bold blue] built-in defaults\n')
        current_config = default_config
    _printTable(current_config, default_config)
    print()

# -- config_verify: checks that all expected keys are present in the user config file
def config_verify():
    config_path = userConfigPath()
    if not _configCheck(config_path, exists=True):
        raise typer.Exit(1)
    user_config = _flatten(_loadUserConfig())
    default_config = _flatten(loadDefaultConfig())
    missing    = [k for k in default_config if k not in user_config]
    unexpected = [k for k in user_config if k not in default_config]
    if not missing and not unexpected:
        print(f'[bold green]SUCCESS:[/bold green] User config [cyan]{config_path}[/cyan] is valid.\n')
        return
    if missing:
        print(f'[bold red]ERROR:[/bold red] {len(missing)} missing key(s):')
        for k in sorted(missing):
            print(f'\t[red]✗[/red] {k} [dim](expected: {default_config[k]})[/dim]')
    if unexpected:
        print(f'[bold red]ERROR:[/bold red] {len(unexpected)} unexpected key(s):')
        for k in sorted(unexpected):
            print(f'\t[red]?[/red] {k}: {user_config[k]}')
    print(f'Run [bold]comms config reset[/bold] to restore defaults.\n')
    raise typer.Exit(1)

# -- config_reset: overwrites the user config file with comMS built-in defaults
def config_reset(force: bool = False):
    config_path = userConfigPath()
    if not force:
        print(f'\n[bold yellow]WARNING:[/bold yellow] This will overwrite [cyan]{config_path}[/cyan] with comMS defaults.')
        if not typer.confirm('All custom settings will be lost. Continue?'):
            print('[dim]Reset cancelled.[/dim]\n')
            raise typer.Exit(0)
    try:
        _writeConfig(loadDefaultConfig())
    except Exception as e:
        print(f'\n[bold red]ERROR:[/bold red] Failed to reset config: {e}')
        raise typer.Exit(1)
    print(f'\n[bold green]SUCCESS:[/bold green] Config at [cyan]{config_path}[/cyan] reset to defaults.\n')

# -- Internal helpers
# -- _loadUserConfig: returns the user config as a dict
def _loadUserConfig() -> dict:
    config_path = userConfigPath()
    if not config_path.exists():
        raise FileNotFoundError(f'No user config found at {config_path}.')
    with config_path.open('rb') as f:
        return tomllib.load(f)

# -- _writeConfig: writes config dict to the user config path
def _writeConfig(config: dict):
    config_path = userConfigPath()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open('wb') as f:
        tomli_w.dump(config, f)

# -- _flatten: returns a flat dict from a nested dict, with dot-separated keys
def _flatten(d: dict, prefix: str = '') -> dict:
    out = {}
    for k, v in d.items():
        key = f'{prefix}.{k}' if prefix else k
        if isinstance(v, dict):
            out.update(_flatten(v, key))
        else:
            out[key] = v
    return out

# -- _configCheck: returns True if the config file existence matches the expected state
def _configCheck(config_path: Path, exists: bool) -> bool:
    if exists:
        if config_path.exists():
            return True
        print(f'\n[bold yellow]WARNING:[/bold yellow] No user config at [cyan]{config_path}[/cyan]\nRun [bold]comms config init[/bold] to create one.\n')
        return False
    else:
        if config_path.exists():
            print(f'\n[bold yellow]WARNING:[/bold yellow] Config already exists at [cyan]{config_path}[/cyan]\nRun [bold]comms config reset[/bold] to reset to defaults.\n')
            return False
        return True

# -- _printTable: prints a Rich table comparing current and default config values
def _printTable(user_config: dict, default_config: dict):
    console = Console()
    table = Table(title='comMS configuration', show_header=True, header_style='bold', show_lines=False)
    table.add_column('Key', style='cyan', no_wrap=True)
    table.add_column('Current value', justify='right')
    table.add_column('Default value', justify='right', style='dim')
    table.add_column('', width=2)
    for key in sorted(default_config.keys()):
        default_val = default_config[key]
        user_val = user_config.get(key, '[bold red]MISSING[/bold red]')
        changed = str(user_val) != str(default_val)
        status = '[yellow]≠[/yellow]' if changed else '[green]✓[/green]'
        user_str = f'[yellow]{user_val}[/yellow]' if changed else str(user_val)
        table.add_row(key, user_str, str(default_val), status)
    console.print(table)