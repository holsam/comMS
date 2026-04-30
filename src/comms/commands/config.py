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

# -- Define constants
CARBAMIDOMETHYL_MOD = 'C+57.0215'    # static carbamidomethylation of Cys
MZ_BIN_WIDTH_HIGH_RES = 0.02    # high-resolution instruments (default)
MZ_BIN_WIDTH_LOW_RES = 1.0005079    # low-resolution instruments
SCORE_FUNC_HIGH_RES = 'xcorr'    # high-resolution instruments (default)
SCORE_FUNC_LOW_RES = 'combined-p-value'    # low-resolution instruments

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


# -- config_set: apply named protocol flags to the user config
def config_set(iodo: bool | None = None, low_res: bool | None = None) -> None:
    if iodo is None and low_res is None:
        print(f'\n[bold yellow]WARNING:[/bold yellow] No flag supplied. Use [bold]--iodo[/bold]/[bold]--no-iodo[/bold] and/or [bold]--low-res[/bold]/[bold]--high-res[/bold].\n')
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
    cfg = _apply_protocol_flags(cfg, iodo=iodo, low_res=low_res)
    try:
        _writeConfig(cfg)
    except Exception as e:
        print(f'\n[bold red]ERROR:[/bold red] Could not write user config: {e}\n')
        raise typer.Exit(1)
    _printSetSummary(iodo=iodo, low_res=low_res)

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

# -- _apply_protocol_flags: returns dictionary of config options
def _apply_protocol_flags(cfg: dict, *, iodo: bool | None, low_res: bool | None) -> dict:
    '''
    Apply protocol flags to a config dictionary in place and return it. Only keys relevant to each flag are touched; all others are preserved.
    iodo flag — owns the cysteine slot in search.mods_spec:
        True  → prepend 1C+57.0215
        False → strip any C+/C- entry
        None  → no change
    low_res flag — owns search.mz_bin_width and search.score_function:
        True  → mz_bin_width=1.0005079, score_function=combined-p-value
        False → mz_bin_width=0.02,      score_function=xcorr
        None  → no change
    '''
    cfg.setdefault('search', {})
    if iodo is not None:
        original = cfg['search'].get('mods_spec', '')
        cfg['search']['mods_spec'] = _apply_iodo(original, iodo=iodo)
    if low_res is not None:
        if low_res:
            cfg['search']['mz_bin_width']   = MZ_BIN_WIDTH_LOW_RES
            cfg['search']['score_function'] = SCORE_FUNC_LOW_RES
        else:
            cfg['search']['mz_bin_width']   = MZ_BIN_WIDTH_HIGH_RES
            cfg['search']['score_function'] = SCORE_FUNC_HIGH_RES
    return cfg

# -- _apply-iodo: returns mod_spec string
def _apply_iodo(mods_spec: str, *, iodo: bool) -> str:
    '''
    Add or remove the carbamidomethylation Cys mod in a Tide mods_spec string.
    The mods_spec format is a comma-separated list of entries such as "1M+15.9949,1Q-17.027".  This function owns the cysteine slot exclusively, so any existing C+... or C-... entry is replaced rather than appended, preventing duplicate or conflicting cysteine modifications.
    '''
    # Split on commas, discard empty strings from a blank mods_spec
    entries = [e.strip() for e in mods_spec.split(',') if e.strip()]
    # Remove any existing cysteine mod (pattern: optional digit(s), C, +/-, digits)
    cys_pattern = re.compile(r'^\d*C[+\-]', re.IGNORECASE)
    entries = [e for e in entries if not cys_pattern.match(e)]
    if iodo:
        # Prepend so cysteine mod appears first
        entries = [f'1{CARBAMIDOMETHYL_MOD}'] + entries
    return ','.join(entries)

# _print_set_summary: prints a summary of changes made
def _printSetSummary(*, iodo: bool | None, low_res: bool | None) -> None:
    '''Print a summary of what config_set changed.'''
    print()
    if iodo is not None:
        action = 'added to' if iodo else 'removed from'
        print(
            f'[bold green]✓[/bold green] [cyan]{CARBAMIDOMETHYL_MOD}[/cyan] '
            f'{action} [dim]search.mods_spec[/dim]'
        )
    if low_res is not None:
        if low_res:
            print(
                f'[bold green]✓[/bold green] Low-resolution mode set: '
                f'[dim]mz_bin_width[/dim] → [cyan]{MZ_BIN_WIDTH_LOW_RES}[/cyan], '
                f'[dim]score_function[/dim] → [cyan]{SCORE_FUNC_LOW_RES}[/cyan]'
            )
        else:
            print(
                f'[bold green]✓[/bold green] High-resolution mode set: '
                f'[dim]mz_bin_width[/dim] → [cyan]{MZ_BIN_WIDTH_HIGH_RES}[/cyan], '
                f'[dim]score_function[/dim] → [cyan]{SCORE_FUNC_HIGH_RES}[/cyan]'
            )
    print()