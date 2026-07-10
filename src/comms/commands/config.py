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

# -- Import internal functions
from comms.utils.context import _normalise_dirs
from comms.utils.log import logMsg
from comms.utils.modspec import apply_custom_mod, apply_organism, apply_protocol_flags, parse_organism_arg
from comms.utils.settings import loadDefaultConfig, globalConfigPath

# -- _confirm: yes/no prompt via logMsg.input, returned as a bool
def _confirm(msg: str, default: bool) -> bool:
    msg = f'{msg} [dim]({"Y/n" if default else "y/N"})[/dim]'
    answer = logMsg.input(msg, choices=['y', 'n'], default='y' if default else 'n', case_sensitive=False, show_choices=False, show_default=False)
    return str(answer).strip().lower() == 'y'

# -- _loadConfigFile: returns the config as a dict
def _loadConfigFile(config_path: Path) -> dict:
    with config_path.open('rb') as f:
        return tomllib.load(f)

# -- _writeConfigTo: writes a config dict to a given path
def _writeConfigTo(config: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('wb') as f:
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

# -- _printTable: prints a Rich table comparing current and default config values
def _printTable(user_config: dict, default_config: dict) -> None:
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

# -- _print_diff_summary: prints only the keys that changed between two flattened config dicts
def _print_diff_summary(before: dict, after: dict) -> None:
    changed = {k: (before.get(k), v) for k, v in after.items() if before.get(k) != v}
    if not changed:
        print('\n[dim]No changes made.[/dim]\n')
        return
    print()
    for key, (old, new) in sorted(changed.items()):
        print(f'[bold green]✓[/bold green] [dim]{key}[/dim]: [dim]{old}[/dim] → [cyan]{new}[/cyan]')
    print()

# -- resolve_or_create: returns the Path to edit, creating it from defaults first if needed
def resolve_or_create(path: Path | None, use_global: bool) -> Path:
    '''
    Resolve the config.toml target and make sure it exists, creating it from bundled defaults if not
    '''
    if use_global:
        target = globalConfigPath()
    elif path is not None:
        _, comms_dir = _normalise_dirs(path)
        target = comms_dir / 'config.toml'
    else:
        bare, nested = Path('config.toml'), Path('comms') / 'config.toml'
        if bare.exists() and nested.exists():
            logMsg.error(f'Both {bare} and {nested} exist in the current directory. Remove one before running comms config here.')
            raise SystemExit(1)
        if bare.exists():
            target = bare
        elif nested.exists():
            target = nested
        else:
            logMsg.warn(f'No local config found in the current directory. Did you mean to use [bold]--global[/bold]?')
            create_answer = _confirm(msg=f'Create default config at {config}', default=True)
            if not create_answer:
                raise SystemExit(0)
            target = nested
    if not target.exists():
        logMsg.debug(f'Creating default config at {target}')
        _writeConfigTo(loadDefaultConfig(), target)
    return target

# -- config_list: prints current config values, highlighting differences from bundled defaults
def config_list(config_path: Path) -> None:
    logMsg('config')
    logMsg.debug(f'Listing config values')
    default_config = _flatten(loadDefaultConfig())
    print(f'\n[bold blue]Current config:[/bold blue] [cyan]{config_path}[/cyan]\n')
    current_config = _flatten(_loadConfigFile(config_path))
    _printTable(current_config, default_config)
    print()

# -- config_verify: checks that all expected keys are present in the config file
def config_verify(config_path: Path) -> None:
    logMsg('config')
    logMsg.debug(f'Verifying config keys at {config_path}')
    user_config = _flatten(_loadConfigFile(config_path))
    default_config = _flatten(loadDefaultConfig())
    missing = [k for k in default_config if k not in user_config]
    unexpected = [k for k in user_config if k not in default_config]
    if not missing and not unexpected:
        logMsg.info(f'Config {config_path} is valid')
        return
    logMsg.error(f'Config invalid: {len(missing)} missing, {len(unexpected)} unexpected key(s)')
    if missing:
        print(f'[bold red]ERROR:[/bold red] {len(missing)} missing key(s):')
        for k in sorted(missing):
            print(f'\t[red]✗[/red] {k} [dim](expected: {default_config[k]})[/dim]')
    if unexpected:
        print(f'[bold red]ERROR:[/bold red] {len(unexpected)} unexpected key(s):')
        for k in sorted(unexpected):
            print(f'\t[red]?[/red] {k}: {user_config[k]}')
    print(f'Run [bold]comms config --reset[/bold] to restore defaults.\n')
    raise SystemExit(1)

# -- config_reset: overwrites the config file with comMS built-in defaults
def config_reset(config_path: Path, force: bool = False) -> None:
    logMsg('config')
    if not force:
        logMsg.warn(f'This will overwrite {config_path} with comMS defaults.')
        if not _confirm('Continue with reset'):
            logMsg.debug('Reset cancelled')
            raise SystemExit(0)
    try:
        _writeConfigTo(loadDefaultConfig(), config_path)
        logMsg.info(f'{config_path} reset to comMS defaults')
    except Exception as e:
        logMsg.error(f'Failed to reset config: {e}')
        raise SystemExit(1)

# -- config_set: apply any given flags to the config file; returns True if anything changed
def config_set(config_path: Path, **flags) -> bool:
    logMsg('config')
    logMsg.debug(f'Applying flags: {flags}')
    if all(v is None for v in flags.values()):
        return False
    try:
        cfg = _loadConfigFile(config_path)
    except Exception as e:
        logMsg.error(f'Failed to read config file: {e}')
        raise SystemExit(1)
    before = _flatten(cfg).copy()
    cfg = apply_protocol_flags(
        cfg,
        iodo=flags.get('iodo'),
        ox=flags.get('ox'),
        phos=flags.get('phos'),
        n_cyc=flags.get('n_cyc'),
        n_ace=flags.get('n_ace'),
        clip_met=flags.get('clip_met'),
        low_res=flags.get('low_res'),
        missed_cleavages=flags.get('missed_cleavages'),
    )
    if flags.get('organism') is not None:
        cfg = apply_organism(cfg, parse_organism_arg(flags['organism']))
    if flags.get('custom') is not None:
        current = cfg.get('index', {}).get('custom_mods', '')
        cfg.setdefault('index', {})['custom_mods'] = apply_custom_mod(current, flags['custom'])
    direct = {
        ('convert', 'gzip'): flags.get('gzip'),
        ('convert', 'format'): flags.get('format'),
        ('convert', 'metadata'): flags.get('metadata'),
        ('search', 'score_function'): flags.get('score_function'),
        ('search', 'min_peaks'): flags.get('min_peaks'),
        ('search', 'precursor_tolerance_ppm'): flags.get('precursor_tolerance_ppm'),
        ('search', 'mz_bin_width'): flags.get('mz_bin_width'),
        ('search', 'threads'): flags.get('threads'),
        ('percolator', 'protein_enzyme'): flags.get('protein_enzyme'),
        ('percolator', 'picked_protein'): flags.get('picked_protein'),
        ('percolator', 'shared_psm'): flags.get('shared_psm'),
        ('quantify', 'measure'): flags.get('measure'),
        ('quantify', 'qvalue_threshold'): flags.get('qvalue_threshold'),
        ('quantify', 'unique_mapping'): flags.get('unique_mapping'),
        ('report', 'min_reps'): flags.get('min_reps'),
        ('report', 'lfc_threshold'): flags.get('lfc_threshold'),
        ('report', 'fdr_threshold'): flags.get('fdr_threshold'),
        ('report', 'top_n_proteins'): flags.get('top_n'),
    }
    for (section, key), value in direct.items():
        if value is not None:
            cfg.setdefault(section, {})[key] = value
    try:
        _writeConfigTo(cfg, config_path)
    except Exception as e:
        logMsg.error(f'Failed to write config file: {e}')
        raise SystemExit(1)
    _print_diff_summary(before, _flatten(cfg))
    return True