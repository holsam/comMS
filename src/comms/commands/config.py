'''
comMS config functions
'''

# ===================== #
# CONFIG INITIALISATION #
# ===================== #
# -- Import external dependencies
import re, tomllib, tomli_w, typer
from pathlib import Path
from rich import print
from rich.console import Console
from rich.table import Table
from typing import Annotated

# -- Import internal functions
from comms.utils.log import logMsg
from comms.utils.settings import loadDefaultConfig, globalConfigPath

# ========================= #
# DEFINE CONFIG SUBCOMMANDS #
# ========================= #
# -- config_init: creates a config file with default settings in the OS config directory
def config_init(config_path: Path | None = None):
    logMsg('config')
    config_path = config_path or globalConfigPath()
    logMsg.debug(f'Checking config path: {config_path}')
    if not _configCheck(config_path, exists=False):
        raise SystemExit(1)
    try:
        logMsg.progress(f'Writing default config to {config_path}')
        _writeConfigTo(loadDefaultConfig(), config_path)
        logMsg.info(f'Config file written to {config_path}')
    except Exception as e:
        logMsg.error(f'Failed to write config: {e}')
        raise SystemExit(1)

# -- config_exists: reports whether a config file exists and prints its path
def config_exists(config_path: Path | None = None):
    logMsg('config')
    config_path = config_path or globalConfigPath()
    logMsg.debug(f'Checking for config at {config_path}')
    if config_path.exists():
        logMsg.info(f'Config file found at {config_path}')
    else:
        logMsg.error(f'No config file at {config_path}')
        raise SystemExit(1)

# -- config_list: prints current config values, highlighting differences from bundled defaults
def config_list(config_path: Path | None = None):
    logMsg('config')
    logMsg.debug(f'Listing config values')
    config_path = config_path or globalConfigPath()
    default_config = _flatten(loadDefaultConfig())
    if _configCheck(config_path, exists=True):
        print(f'[bold blue]Current config:[/bold blue] [cyan]{config_path}[/cyan]\n')
        current_config = _flatten(_loadConfigFile(config_path))
    else:
        print(f'[bold blue]Current config:[/bold blue] built-in defaults\n')
        current_config = default_config
    _printTable(current_config, default_config)
    print()

# -- config_verify: checks that all expected keys are present in the config file
def config_verify(config_path: Path | None = None):
    logMsg('config')
    config_path = config_path or globalConfigPath()
    logMsg.debug(f'Verifying config keys at {config_path}')
    if not _configCheck(config_path, exists=True):
        logMsg.error(f'No config to verify at {config_path}')
        raise SystemExit(1)
    user_config = _flatten(_loadConfigFile(config_path))
    default_config = _flatten(loadDefaultConfig())
    missing = [k for k in default_config if k not in user_config]
    unexpected = [k for k in user_config if k not in default_config]
    if not missing and not unexpected:
        logMsg.info(f'User config {config_path} is valid')
        return
    logMsg.error(f'User config invalid: {len(missing)} missing, {len(unexpected)} unexpected key(s)')
    if missing:
        logMsg.warn(f'Missing keys in config: {missing}')
        print(f'[bold red]ERROR:[/bold red] {len(missing)} missing key(s):')
        for k in sorted(missing):
            print(f'\t[red]✗[/red] {k} [dim](expected: {default_config[k]})[/dim]')
    if unexpected:
        logMsg.warn(f'Unexpected keys in config: {unexpected}')
        print(f'[bold red]ERROR:[/bold red] {len(unexpected)} unexpected key(s):')
        for k in sorted(unexpected):
            print(f'\t[red]?[/red] {k}: {user_config[k]}')
    print(f'Run [bold]comms config reset[/bold] to restore defaults.\n')
    raise SystemExit(1)

# -- config_reset: overwrites the config file with comMS built-in defaults
def config_reset(config_path: Path | None = None, force: bool = False):
    logMsg('config')
    config_path = config_path or globalConfigPath()
    if not force:
        logMsg.warn(f'This will overwrite {config_path} with comMS defaults.')
        if not typer.confirm('All custom settings will be lost. Continue?'):
            logMsg.debug(f'Reset cancelled')
            raise SystemExit(0)
    try:
        _writeConfigTo(loadDefaultConfig(), config_path)
        logMsg.info(f'{config_path} reset to comMS defaults')
    except Exception as e:
        logMsg.error(f'Failed to reset config: {e}')
        raise SystemExit(1)

# -- config_set: apply named flags to the config
def config_set(
    config_path: Path | None = None,
    iodo: bool | None = None,
    low_res: bool | None = None,
    organism: list[str] | None = None,
    ox: bool | None = None,
    phos: bool | None = None,
    n_cyc: bool | None = None,
    n_ace: bool | None = None,
    custom: str | None = None,
    clip_met: bool | None = None,
) -> None:
    # Set up logger
    logMsg('config')
    logMsg.debug(f'Applying set flags: iodo={iodo}; ox={ox}; phos={phos}; n_cyc={n_cyc}; n_ace={n_ace}; low_res={low_res}; organism={organism}; custom={custom!r}; clip_met={clip_met}')
    # Check at least one flag set
    if all(v is None for v in (iodo, ox, phos, n_cyc, n_ace, low_res, organism, custom, clip_met)):
        logMsg.error(f'No flags supplied to config set')
        raise SystemExit(1)
    # Check if  config exists
    config_path = config_path or globalConfigPath()
    if not config_path.exists():
        logMsg.debug(f'No config found, creating from defaults at {config_path}')
        _writeConfigTo(loadDefaultConfig(), path=config_path)
    # Load config
    try:
        cfg = _loadConfigFile(config_path)
    except Exception as e:
        logMsg.error(f'Failed to read config file: {e}')
        raise SystemExit(1)
    # Apply any passed flags
    cfg = _apply_protocol_flags(
        cfg,
        iodo=iodo,
        ox=ox,
        phos=phos,
        n_cyc=n_cyc,
        n_ace=n_ace,
        low_res=low_res,
        clip_met=clip_met
    )
    if organism is not None:
        cfg = _apply_organism(cfg, _parse_organism_arg(organism))
    if custom is not None:
        current = cfg.get('index', {}).get('custom_mods', '')
        cfg.setdefault('index', {})['custom_mods'] = _apply_custom_mod(current, custom)
    # Write updated config
    try:
        _writeConfigTo(cfg, config_path)
    except Exception as e:
        logMsg.error(f'Failed to write config file: {e}')
        raise SystemExit(1)
    # Print summary
    _printSetSummary(iodo=iodo, ox=ox, phos=phos, n_cyc=n_cyc, n_ace=n_ace, low_res=low_res, organism=organism, custom=custom, clip_met=clip_met)
    print()


# ======================= #
# DEFINE INTERNAL HELPERS #
# ======================= #
# -- _resolveConfigTarget: returns the Path to edit (global user config or a local file)
def _resolveConfigTarget(target: str | None) -> Path:
    if target is None or target.upper() == 'GLOBAL':
        return globalConfigPath()
    return Path(target)

# -- _loadConfigFile: returns the config as a dict
def _loadConfigFile(config_path: Path | None = None) -> dict:
    config_path = config_path or globalConfigPath()
    if not config_path.exists():
        raise FileNotFoundError(f'No config found at {config_path}.')
    with config_path.open('rb') as f:
        return tomllib.load(f)

# -- _writeConfigTo: writes a config dict to a given path
def _writeConfigTo(config: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('wb') as f:
        tomli_w.dump(config, f)

# -- _writeConfig: writes config dict to the global config path
def _writeConfig(config: dict):
    _writeConfigTo(config, globalConfigPath())

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
        print(f'\n[bold yellow]WARNING:[/bold yellow] No config at [cyan]{config_path}[/cyan]\nRun [bold]comms config init[/bold] to create one.\n')
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


# ========================= #
# DEFINE CONFIG SET HELPERS #
# ========================= #
# _mod_summary_line: prints a s
def _mod_summary_line(flag: bool | None, mod: str, key: str):
    '''
    Print a single ✓ line for a boolean mod flag, or nothing if flag is None
    '''
    if flag is None:
        return
    print(f'[bold green]✓[/bold green] [dim]{key}[/dim] → [cyan]{mod}[/cyan]')

# _print_set_summary: prints a summary of changes made
def _printSetSummary(
    *,
    iodo: bool | None,
    ox: bool | None,
    phos: bool | None,
    n_cyc: bool | None,
    n_ace: bool | None,
    low_res: bool | None,
    organism: list[str] | None,
    custom: str | None,
    clip_met: bool | None,
) -> None:
    '''
    Print a summary of what config_set changed
    '''
    print()
    _mod_summary_line(iodo, CARBAMIDOMETHYL_MOD, f'index.{'fixed_mods'}')
    _mod_summary_line(ox, MET_OX_MOD, 'index.mods_spec')
    _mod_summary_line(phos, PHOSPHO_MOD, 'index.mods_spec')
    if custom is not None:
        if custom == '':
            print(f'[bold green]✓[/bold green] Custom mods cleared: [dim]index.custom_mods[/dim] → [cyan](empty)[/cyan]')
        else:
            print(f'[bold green]✓[/bold green] Custom mod added: [dim]index.custom_mods[/dim] → [cyan]{custom}[/cyan]')
    _mod_summary_line(n_cyc, NCYC_MOD, f'index.{'nterm_peptide_mods_spec'}')
    _mod_summary_line(n_ace, NACE_MOD, f'index.{'nterm_protein_mods_spec'}')
    if clip_met is not None:
        value = 'true' if clip_met else 'false'
        print(f'[bold green]✓[/bold green] Clipped N-terminal methionine set: [dim]index.clip_n_met[/dim] → to [cyan]{value}[/cyan]')
    if low_res is not None:
        if low_res:
            print(f'[bold green]✓[/bold green] Low-resolution mode set: [dim]search.mz_bin_width[/dim] → [cyan]{MZ_BIN_WIDTH_LOW_RES}[/cyan], [dim]search.score_function[/dim] → [cyan]{SCORE_FUNC_LOW_RES}[/cyan]')
        else:
            print(f'[bold green]✓[/bold green] High-resolution mode set: [dim]search.mz_bin_width[/dim] → [cyan]{MZ_BIN_WIDTH_HIGH_RES}[/cyan], [dim]search.score_function[/dim] → [cyan]{SCORE_FUNC_HIGH_RES}[/cyan]')
    if organism is not None:
        for item in organism:
            key, _, pattern = item.partition('=')
            key = ''.join(key.split())
            pattern = ''.join(pattern.split())
            print(f'[bold green]✓[/bold green] Organism pattern set: [dim]organism[/dim] → [cyan]{key}[/cyan]: [cyan]{pattern}[/cyan]')
    print()