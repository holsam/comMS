'''
comMS config functions
'''

# -- Import external dependencies
import re, tomllib, tomli_w, typer
from pathlib import Path
from rich import print
from rich.console import Console
from rich.table import Table
from typing import Annotated

# -- Import internal functions
from comms.utils.settings import loadDefaultConfig, userConfigPath

# -- Public constant: cysteine mod string added by iodoacetamide alkylation
CARBAMIDOMETHYL_MOD = 'C+57.0215'   # static carbamidomethylation of Cys


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


# -- config_set: apply a named protocol flag to the user config
def config_set(iodo: bool | None) -> None:
    if iodo is None:
        print('\n[bold yellow]WARNING:[/bold yellow] No flag supplied. '
              'Use [bold]--iodo[/bold] or [bold]--no-iodo[/bold].\n')
        raise typer.Exit(1)
    config_path = userConfigPath()
    # Auto-create from defaults if no user config exists yet
    if not config_path.exists():
        print(f'\n[dim]No user config found — creating one from defaults at [cyan]{config_path}[/cyan][/dim]')
        _writeConfig(loadDefaultConfig())
    try:
        cfg = _loadUserConfig()
    except Exception as e:
        print(f'\n[bold red]ERROR:[/bold red] Could not read user config: {e}\n')
        raise typer.Exit(1)
    original_mods = cfg.get('search', {}).get('mods_spec', '')
    updated_mods  = _apply_protocol_flags(original_mods, iodo=iodo)
    cfg.setdefault('search', {})['mods_spec'] = updated_mods
    try:
        _writeConfig(cfg)
    except Exception as e:
        print(f'\n[bold red]ERROR:[/bold red] Could not write user config: {e}\n')
        raise typer.Exit(1)
    action = 'added to' if iodo else 'removed from'
    if original_mods == updated_mods:
        print(f'\n[dim]No change — [cyan]{CARBAMIDOMETHYL_MOD}[/cyan] was already {"present in" if iodo else "absent from"} mods_spec.[/dim]\n')
    else:
        print(f'\n[bold green]SUCCESS:[/bold green] [cyan]{CARBAMIDOMETHYL_MOD}[/cyan] {action} mods_spec.\n'
              f'  Before: {original_mods or "(empty)"}\n'
              f'  After: {updated_mods}\n')

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

# -- _apply_protocol_flags: returns string for mods_spec
def _apply_protocol_flags(mods_spec: str, *, iodo: bool) -> str:
    '''
    Add or remove the carbamidomethylation Cys mod in a Tide mods_spec string.
    '''
    # Split on commas, discard empty strings from a blank mods_spec
    entries = [e.strip() for e in mods_spec.split(',') if e.strip()]
    # Remove any existing cysteine mod (pattern: optional digit(s), C, +/-, digits)
    cys_pattern = re.compile(r'^\d*C[+\-]', re.IGNORECASE)
    entries = [e for e in entries if not cys_pattern.match(e)]
    if iodo:
        # Prepend so cysteine mod appears first — purely cosmetic but consistent
        entries = [f'1{CARBAMIDOMETHYL_MOD}'] + entries
    return ','.join(entries)