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
from comms.utils.settings import loadDefaultConfig, userConfigPath

# -- Define modification constants
CARBAMIDOMETHYL_MOD = 'C+57.0215'    # static carbamidomethylation of Cys
MET_OX_MOD = '1M+15.9949'    # variable Met oxidation
PHOSPHO_MOD = '1STY+79.966331'    # variable STY phosphorylation
NCYC_MOD = '1Q-17.027'    # N-terminal Gln cyclisation
NACE_MOD = '1X+42.011'    # N-terminal protein acetylation
FIXED_MODS_KEY = 'fixed_mods'
NTERM_PEPTIDE_KEY = 'nterm_peptide_mods_spec'
NTERM_PROTEIN_KEY = 'nterm_protein_mod_spec'
MANAGED_MOD_PATTERNS: dict[str, str] = {
    r'^\d*C[+\-]': '--iodo / --no-iodo',
    r'^\d*M\+15\.9949': '--ox / --no-ox',
    r'^\d*STY\+79\.966331': '--phos / --no-phos',
}    # mods that --custom is not allowed to duplicate (maps the residue/pattern that identifies each managed mod to its flag name)

# -- Define resolution constants
MZ_BIN_WIDTH_HIGH_RES = 0.02    # high-resolution instruments (default)
MZ_BIN_WIDTH_LOW_RES = 1.0005079    # low-resolution instruments
SCORE_FUNC_HIGH_RES = 'xcorr'    # high-resolution instruments (default)
SCORE_FUNC_LOW_RES = 'combined-p-value'    # low-resolution instruments


# ========================= #
# DEFINE CONFIG SUBCOMMANDS #
# ========================= #
# -- config_init: creates a user config file with default settings in the OS config directory
def config_init():
    log = logMsg('config')
    log.debug(f'Checking config path: {userConfigPath()}')
    config_path = userConfigPath()
    if not _configCheck(config_path, exists=False):
        raise SystemExit(1)
    try:
        log.info(f'Writing default config to: {config_path}')
        defaults = loadDefaultConfig()
        _writeConfig(defaults)
        print(f'[bold green]SUCCESS:[/bold green] User config written to [cyan]{config_path}[/cyan]\n')
    except Exception as e:
        log.error(f'Failed to write config: {e}')
        print(f'[bold red]ERROR:[/bold red] Could not write config: {e}\n')
        raise SystemExit(1)

# -- config_exists: reports whether a user config file exists and prints its path
def config_exists():
    log = logMsg('config')
    log.debug(f'Checking for user config at: {userConfigPath()}')
    config_path = userConfigPath()
    if config_path.exists():
        print(f'[bold green]SUCCESS:[/bold green] User config found at [cyan]{config_path}[/cyan]\n')
    else:
        print(f'[bold yellow]WARNING:[/bold yellow] No user config at [cyan]{config_path}[/cyan]\nRun [bold]comms config init[/bold] to create one.\n')
        raise SystemExit(1)

# -- config_list: prints current config values, highlighting differences from bundled defaults
def config_list():
    log = logMsg('config')
    log.debug(f'Listing config values')
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
    log = logMsg('config')
    log.debug(f'Verifying config keys at: {userConfigPath()}')
    config_path = userConfigPath()
    if not _configCheck(config_path, exists=True):
        raise SystemExit(1)
    user_config = _flatten(_loadUserConfig())
    default_config = _flatten(loadDefaultConfig())
    missing = [k for k in default_config if k not in user_config]
    unexpected = [k for k in user_config if k not in default_config]
    if not missing and not unexpected:
        print(f'[bold green]SUCCESS:[/bold green] User config [cyan]{config_path}[/cyan] is valid.\n')
        return
    if missing:
        log.warn(f'Missing keys in user config: {missing}')
        print(f'[bold red]ERROR:[/bold red] {len(missing)} missing key(s):')
        for k in sorted(missing):
            print(f'\t[red]✗[/red] {k} [dim](expected: {default_config[k]})[/dim]')
    if unexpected:
        log.warn(f'Unexpected keys in user config: {unexpected}')
        print(f'[bold red]ERROR:[/bold red] {len(unexpected)} unexpected key(s):')
        for k in sorted(unexpected):
            print(f'\t[red]?[/red] {k}: {user_config[k]}')
    print(f'Run [bold]comms config reset[/bold] to restore defaults.\n')
    raise SystemExit(1)

# -- config_reset: overwrites the user config file with comMS built-in defaults
def config_reset(force: bool = False):
    log = logMsg('config')
    config_path = userConfigPath()
    if not force:
        print(f'\n[bold yellow]WARNING:[/bold yellow] This will overwrite [cyan]{config_path}[/cyan] with comMS defaults.')
        if not typer.confirm('All custom settings will be lost. Continue?'):
            print('[dim]Reset cancelled.[/dim]\n')
            raise SystemExit(0)
    try:
        log.info(f'Resetting config to defaults at: {config_path}')
        _writeConfig(loadDefaultConfig())
    except Exception as e:
        log.error(f'Failed to reset config: {e}')
        print(f'\n[bold red]ERROR:[/bold red] Failed to reset config: {e}')
        raise SystemExit(1)
    print(f'\n[bold green]SUCCESS:[/bold green] Config at [cyan]{config_path}[/cyan] reset to defaults.\n')

# -- config_set: apply named flags to the user config
def config_set(
    iodo: bool | None = None,
    low_res: bool | None = None,
    organism: list[str] | None = None,
    mbr: bool | None = None,
    ox: bool | None = None,
    phos: bool | None = None,
    n_cyc: bool | None = None,
    n_ace: bool | None = None,
    custom: str | None = None,
) -> None:
    # Set up logger
    log = logMsg('config')
    log.debug(f'Applying set flags: iodo={iodo}; ox={ox}; phos={phos}; n_cyc={n_cyc}; n_ace={n_ace}; low_res={low_res}; organism={organism}; mbr={mbr}; custom={custom!r}')
    # Check at least one flag set
    if all(v is None for v in (iodo, ox, phos, n_cyc, n_ace, low_res, organism, mbr, custom)):
        log.warn(f'No flag supplied to config set.')
        print(f'\n[bold yellow]WARNING:[/bold yellow] No flag supplied. Use [bold]comms config set --help[/bold]/[bold]to see available options.\n')
        raise SystemExit(1)
    # Check if user config exists
    config_path = userConfigPath()
    if not config_path.exists():
        log.debug(f'No user config found — creating from defaults at: {config_path}')
        print(f'\n[dim]No user config found — creating one from defaults at [cyan]{config_path}[/cyan][/dim]')
        _writeConfig(loadDefaultConfig())
    # Load user config
    try:
        cfg = _loadUserConfig()
    except Exception as e:
        log.error(f'Failed to read user config: {e}')
        print(f'\n[bold red]ERROR:[/bold red] Could not read user config: {e}\n')
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
        mbr=mbr,
    )
    if organism is not None:
        cfg = _apply_organism(cfg, _parse_organism_arg(organism))
    if custom is not None:
        current = cfg.get('search', {}).get('custom_mods', '')
        cfg.setdefault('search', {})['custom_mods'] = _apply_custom_mod(current, custom)
    # Write updated config
    try:
        _writeConfig(cfg)
    except Exception as e:
        log.error(f'Failed to write user config: {e}')
        print(f'\n[bold red]ERROR:[/bold red] Could not write user config: {e}\n')
        raise SystemExit(1)
    # Print summary
    _printSetSummary(iodo=iodo, ox=ox, phos=phos, n_cyc=n_cyc, n_ace=n_ace, low_res=low_res, organism=organism, mbr=mbr, custom=custom)
    print()


# ======================= #
# DEFINE INTERNAL HELPERS #
# ======================= #
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


# ========================= #
# DEFINE CONFIG SET HELPERS #
# ========================= #
# -- _apply_protocol_flags: returns dictionary of config options
def _apply_protocol_flags(
    cfg: dict,
    *,
    iodo: bool | None = None,
    ox: bool | None = None,
    phos: bool | None = None,
    n_cyc: bool | None = None,
    n_ace: bool | None = None,
    low_res: bool | None = None,
    mbr: bool | None = None,
) -> dict:
    '''
    Apply protocol flags to a config dictionary and return it
        iodo — owns the Cys slot in search.mods_spec exclusively
        ox — adds/removes 1M+15.9949 in search.mods_spec
        phos — adds/removes 1STY+79.966331 in search.mods_spec
        n_cyc — adds/removes 1Q-17.027 in search.nterm_peptide_mods_spec
        n_ace — adds/removes 1X+42.011 in search.nterm_protein_mod_spec
        low_res — sets search.mz_bin_width and search.score_function
        mbr — sets lfq.match_between_runs
    '''
    cfg.setdefault('search', {})
    cfg['search'].setdefault(FIXED_MODS_KEY, '')
    cfg['search'].setdefault(NTERM_PEPTIDE_KEY, '')
    cfg['search'].setdefault(NTERM_PROTEIN_KEY, '')
    if iodo is not None:
        cfg['search'][FIXED_MODS_KEY] = _apply_iodo(cfg['search'].get(FIXED_MODS_KEY, ''), iodo=iodo)
    if ox is not None:
        spec = cfg['search'].get('mods_spec', '')
        if ox:
            cfg['search']['mods_spec'] = _apply_mod(spec, mod=MET_OX_MOD)
        else:
            cfg['search']['mods_spec'] = _apply_mod(spec, mod='', exclusive_pattern=r'^\d*M\+15\.9949')
    if phos is not None:
        spec = cfg['search'].get('mods_spec', '')
        if phos:
            cfg['search']['mods_spec'] = _apply_mod(spec, mod=PHOSPHO_MOD)
        else:
            cfg['search']['mods_spec'] = _apply_mod(spec, mod='', exclusive_pattern=r'^\d*STY\+79\.966331')
    if n_cyc is not None:
        spec = cfg['search'].get(NTERM_PEPTIDE_KEY, '')
        if n_cyc:
            cfg['search'][NTERM_PEPTIDE_KEY] = _apply_mod(spec, mod=NCYC_MOD)
        else:
            cfg['search'][NTERM_PEPTIDE_KEY] = _apply_mod(spec, mod='', exclusive_pattern=r'^\d*Q\-17\.027')
    if n_ace is not None:
        spec = cfg['search'].get(NTERM_PROTEIN_KEY, '')
        if n_ace:
            cfg['search'][NTERM_PROTEIN_KEY] = _apply_mod(spec, mod=NACE_MOD)
        else:
            cfg['search'][NTERM_PROTEIN_KEY] = _apply_mod(spec, mod='', exclusive_pattern=r'^\d*X\+42\.011')
    if low_res is not None:
        if low_res:
            cfg['search']['mz_bin_width']   = MZ_BIN_WIDTH_LOW_RES
            cfg['search']['score_function'] = SCORE_FUNC_LOW_RES
        else:
            cfg['search']['mz_bin_width']   = MZ_BIN_WIDTH_HIGH_RES
            cfg['search']['score_function'] = SCORE_FUNC_HIGH_RES
        logMsg.debug(f'low_res flag applied — mz_bin_width: {cfg["search"]["mz_bin_width"]}, score_function: {cfg["search"]["score_function"]}')
    if mbr is not None:
        cfg.setdefault('lfq', {})
        cfg['lfq']['match_between_runs'] = 'true' if mbr else 'false'
        logMsg.debug(f'mbr flag applied — match_between_runs: {cfg['lfq']['match_between_runs']}')
    return cfg

# -- _apply_mod: returns mod_spec string
def _apply_mod(mods_spec: str, mod: str, exclusive_pattern: str | None = None) -> str:
    '''
    Add or remove a mod entry in a Tide mods_spec string.
    '''
    # Split on commas, discard empty strings from a blank mods_spec
    entries = [e.strip() for e in mods_spec.split(',') if e.strip()]
    if exclusive_pattern:
        pattern = re.compile(exclusive_pattern, re.IGNORECASE)
        entries = [e for e in entries if not pattern.match(e)]
    elif mod == '':
        pass
    else:
        entries = [e for e in entries if e != mod]
    if mod:
        entries = [mod] + entries
    return ','.join(entries)

# -- _apply-iodo: returns fixed_mods string
def _apply_iodo(fixed_mods: str, iodo: bool) -> str:
    '''
    Add or remove the carbamidomethylation Cys mod in a Tide fixed_mods string
    '''
    # Split on commas, discard empty strings from a blank mods_spec
    entries = [e.strip() for e in fixed_mods.split(',') if e.strip()]
    entries = [e for e in entries if e != CARBAMIDOMETHYL_MOD]
    if iodo:
        entries = [CARBAMIDOMETHYL_MOD] + entries
    result = ','.join(entries)
    logMsg.debug(f'iodo flag applied — mods_spec updated to: {result}')
    return result

def _apply_custom_mod(custom_mods: str, new_entry: str) -> str:
    '''
    Add a custom mod entry to the custom_mods string, or clear all custom mods if new_entry is an empty string
    '''
    if new_entry == '':
        return ''

    # Check against managed mod patterns
    for pattern, flag_name in MANAGED_MOD_PATTERNS.items():
        if re.match(pattern, new_entry, re.IGNORECASE):
            print(
                f'\n[bold yellow]WARNING:[/bold yellow] [cyan]{new_entry}[/cyan] is managed by the [bold]{flag_name}[/bold] flag. Use that flag to add modification.\n'
            )
            return custom_mods
    # Split on commas, discard empty strings from a blank mods_spec
    entries = [e.strip() for e in custom_mods.split(',') if e.strip()]
    if new_entry not in entries:
        entries.append(new_entry)
    return ','.join(entries)

# -- _apply_organism: returns config dict with organism section replaced
def _apply_organism(cfg: dict, organism: dict[str, str]) -> dict:
    '''
    Replace the [organism] section of the user config with the supplied dictionary.
    '''
    cfg['organism'] = organism
    logMsg.debug(f'organism section set to: {organism}')
    return cfg

# -- _parse_organism_arg: returns dict parsed from list of 'Key=Pattern' strings
def _parse_organism_arg(pairs: list[str]) -> dict[str, str]:
    '''
    Parse a list of 'Label=Pattern' strings into a dict.
    '''
    result = {}
    for item in pairs:
        if '=' not in item:
            logMsg.error(f'Invalid organism argument ({item}). Expected format: Organism=Pattern')
            print(f'\n[bold red]ERROR:[/] Invalid organism argument ({item}). Expected format: Organism=Pattern')
            raise SystemExit(1)
        key, _, pattern = item.partition('=')
        key = ''.join(key.split())
        pattern = ''.join(pattern.split())
        if not key:
            logMsg.error(f'Empty label in organism argument ({item}).')
            print(f'\n[bold red]ERROR:[/] Empty label in organism argument ({item})')
            raise SystemExit(1)
        if not pattern:
            logMsg.error(f'Empty pattern in organism argument ({item}).')
            print(f'\n[bold red]ERROR:[/] Empty pattern in organism argument ({item})')
            raise SystemExit(1)
        result[key] = pattern
    return result

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
    mbr: bool | None,
    custom: str | None,
) -> None:
    '''
    Print a summary of what config_set changed
    '''
    print()
    _mod_summary_line(iodo, CARBAMIDOMETHYL_MOD, f'search.{FIXED_MODS_KEY}')
    _mod_summary_line(ox, MET_OX_MOD, 'search.mods_spec')
    _mod_summary_line(phos, PHOSPHO_MOD, 'search.mods_spec')
    if custom is not None:
        if custom == '':
            print(f'[bold green]✓[/bold green] Custom mods cleared: [dim]search.custom_mods[/dim] → [cyan](empty)[/cyan]')
        else:
            print(f'[bold green]✓[/bold green] Custom mod added: [dim]search.custom_mods[/dim] → [cyan]{custom}[/cyan]')
    _mod_summary_line(n_cyc, NCYC_MOD, f'search.{NTERM_PEPTIDE_KEY}')
    _mod_summary_line(n_ace, NACE_MOD, f'search.{NTERM_PROTEIN_KEY}')
    if low_res is not None:
        if low_res:
            print(f'[bold green]✓[/bold green] Low-resolution mode set: [dim]mz_bin_width[/dim] → [cyan]{MZ_BIN_WIDTH_LOW_RES}[/cyan], [dim]score_function[/dim] → [cyan]{SCORE_FUNC_LOW_RES}[/cyan]')
        else:
            print(f'[bold green]✓[/bold green] High-resolution mode set: [dim]mz_bin_width[/dim] → [cyan]{MZ_BIN_WIDTH_HIGH_RES}[/cyan], [dim]score_function[/dim] → [cyan]{SCORE_FUNC_HIGH_RES}[/cyan]')
    if organism is not None:
        for item in organism:
            key, _, pattern = item.partition('=')
            key = ''.join(key.split())
            pattern = ''.join(pattern.split())
            print(f'[bold green]✓[/bold green] Organism pattern set: [dim]organism[/dim] → [cyan]{key}[/cyan]: [cyan]{pattern}[/cyan]')
    if mbr is not None:
        value = 'true' if mbr else 'false'
        print(f'[bold green]✓[/bold green] Match between runs set: [dim]lfq[/dim] → to [cyan]{value}[/cyan]')
    print()