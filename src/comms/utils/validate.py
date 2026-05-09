'''
comMS binary validation utility functions
'''

# -- Import external dependencies
import platform, re, shutil, subprocess
from pathlib import Path
from typing import Optional
from rich import print

# -- Import internal functions
from comms.utils.log import logMsg
from comms.utils import paths as pathutil

# -- Define version constraints
_CRUX_MIN_LFQ = (5, 0, 0)    # minimum Crux version required for the lfq command
_TRFP_MIN_MONO = (2, 0, 0)    # TRFP versions below this require Mono on non-Windows

# -- validate: returns a tuple of Paths to Crux and TRFP binaries
def validate(
    check_crux: bool = False,
    check_trfp: bool = False,
    allow_lfq: bool = False,
) -> tuple[Optional[Path], Optional[Path]]:
    bin_dir = pathutil.repoBinDir()
    crux_bin: Optional[Path] = None
    trfp_path: Optional[Path] = None
    if check_crux:
        crux_bin = _check_crux(bin_dir, allow_lfq=allow_lfq)
    if check_trfp:
        trfp_path = _check_trfp(bin_dir)
    return crux_bin, trfp_path

# -- _find_all_crux: returns a list of Paths to Crux binaries
def _find_all_crux(bin_dir: Path) -> list[Path]:
    '''
    Return all Crux binaries found under bin_dir, matching the expected layout of crux-<version>.<platform>/bin/crux
    '''
    return list(bin_dir.glob('crux*/bin/crux'))

# -- _find_all_trfp: returns a list of Paths to Crux binaries
def _find_all_trfp(bin_dir: Path) -> list[Path]:
    '''
    Return all ThermoRawFileParser binaries found under bin_dir, matching .exe and native binaries
    '''
    matches = list(bin_dir.glob('*/ThermoRawFileParser.exe'))
    matches += list(bin_dir.glob('*/ThermoRawFileParser'))
    return matches

# -- _select_best: returns a tuple of Path and version for the most recent binary past as candidates
def _select_best(
    candidates: list[Path],
    get_version_fn,
) -> Optional[tuple[Path, tuple[int, ...]]]:
    '''
    Return candidate with highest version
    '''
    best_path: Optional[Path] = None
    best_version: Optional[tuple[int, ...]] = None
    for candidate in candidates:
        version = get_version_fn(candidate)
        if version is None:
            logMsg.debug(f'Could not determine version for candidate: {candidate}')
            continue
        if best_version is None or version > best_version:
            best_version = version
            best_path = candidate
    if best_path is None:
        return None
    return best_path, best_version

# -- _parse_version: returns a tuple of ints corresponding to a parsed version number
def _parse_version(version_str: str) -> Optional[tuple[int, ...]]:
    '''
    Parse a dotted version string such as "4.3.2" or "1.4.5" into a tuple of ints
    '''
    match = re.search(r'(\d+\.\d+(?:\.\d+)*)', version_str)
    if not match:
        return None
    try:
        return tuple(int(part) for part in match.group(1).split('.'))
    except ValueError:
        return None

# -- _check_crux: returns a Path to the most up-to-date Crux binary
def _check_crux(bin_dir: Path, allow_lfq: bool) -> Path:
    '''
    Locate all Crux installations, select the most up-to-date, enforce any version constraints, and return the path to the selected binary
    '''
    logMsg.debug('validate: checking Crux binary')
    print('validate: checking Crux binary')
    crux_candidates = _find_all_crux(bin_dir)
    print(crux_candidates)
    if not crux_candidates:
        logMsg.error(f'Crux binary not found under: {bin_dir}')
        print(f'\n[bold red]ERROR:[/bold red] Crux binary not found under [cyan]{bin_dir}[/cyan].\n')
        raise SystemExit(1)
    result = _select_best(crux_candidates, _get_crux_version)
    if result is None:
        logMsg.error('Could not determine version for any Crux installation')
        print('\n[bold red]ERROR:[/bold red] Could not determine Crux version for any installation found - please check any Crux installations.\n')
        raise SystemExit(1)
    crux_bin, version = result
    version_str = '.'.join(str(v) for v in version)
    if len(crux_candidates) > 1:
        logMsg.info(f'{len(crux_candidates)} Crux installations found. Using most recent: v{version_str} at {crux_bin}')
        print(f'[dim]Found {len(crux_candidates)} Crux installations. Using most recent: v{version_str} ([cyan]{crux_bin}[/cyan])[/dim]')
    logMsg.debug(f'Crux version: {version_str} at {crux_bin}')
    if allow_lfq and version < _CRUX_MIN_LFQ:
        min_str = '.'.join(str(v) for v in _CRUX_MIN_LFQ)
        logMsg.error(f'Crux {version_str} does not support lfq (requires >= {min_str})')
        print(f'\n[bold red]ERROR:[/bold red] The [bold]lfq[/bold] command requires Crux >= [cyan]{min_str}[/cyan], but the most recent installed version is [cyan]{version_str}[/cyan].\n')
        raise SystemExit(1)
    return crux_bin

# -- _check_trfp: returns a Path to the most up-to-date ThermoRawFileParser binary
def _check_trfp(bin_dir: Path) -> Path:
    '''
    Locate all ThermoRawFileParser installations, select the most up-to-date, check for Mono if needed, and return the path to the selected binary
    '''
    logMsg.debug('validate: checking ThermoRawFileParser binary')
    trfp_candidates = _find_all_trfp(bin_dir)
    if not trfp_candidates:
        logMsg.error(f'ThermoRawFileParser not found under: {bin_dir}')
        print(f'\n[bold red]ERROR:[/bold red] ThermoRawFileParser not found under [cyan]{bin_dir}[/cyan].\n')
        raise SystemExit(1)
    result = _select_best(trfp_candidates, _get_trfp_version)
    if result is None:
        logMsg.error('Could not determine version for any ThermoRawFileParser installation')
        print('\n[bold red]ERROR:[/bold red] Could not determine ThermoRawFileParser version for any installation found - please check any ThermoRawFileParser installations.\n')
        raise SystemExit(1)
    trfp_path, version = result
    version_str = '.'.join(str(v) for v in version)
    if len(trfp_candidates) > 1:
        logMsg.info(f'{len(trfp_candidates)} ThermoRawFileParser installations found; using most recent: v{version_str} at {trfp_path}')
        print(f'[dim]Found {len(trfp_candidates)} ThermoRawFileParser installations. Using most recent: v{version_str} ([cyan]{trfp_path}[/cyan])[/dim]')
    logMsg.debug(f'ThermoRawFileParser version: {version_str} at {trfp_path}')
    if version < _TRFP_MIN_MONO and platform.system() != 'Windows':
        logMsg.debug('TRFP < 2.0.0 on non-Windows: checking for Mono')
        if shutil.which('mono') is None:
            logMsg.error(f'Mono not found; required for ThermoRawFileParser {version_str} on non-Windows')
            print(f'\n[bold red]ERROR:[/bold red] ThermoRawFileParser [cyan]{version_str}[/cyan] requires [bold]Mono[/bold] on Linux/macOS, but Mono was not found on PATH.\nInstall it with [bold]brew install mono[/bold] (macOS) or [bold]apt install mono-complete[/bold] (Debian/Ubuntu), or upgrade to ThermoRawFileParser >= 2.0.0.\n')
            raise SystemExit(1)
    return trfp_path

# -- _get_crux_version: returns a tuple of ints corresponding to parsed version number
def _get_crux_version(crux_bin: Path) -> Optional[tuple[int, ...]]:
    '''
    Run `crux version` and parse the version tuple from its output.
    '''
    try:
        result = subprocess.run(
            [str(crux_bin), 'version'],
            capture_output=True,
            text=True,
            check=False,
        )
        output = result.stdout + result.stderr
    except Exception as e:
        logMsg.error(f'Failed to run crux version: {e}')
        return None
    # Match the canonical "Crux version X.Y.Z" line; ignore the build suffix
    match = re.search(r'Crux version\s+(\d+\.\d+(?:\.\d+)*)', output, re.IGNORECASE)
    if not match:
        logMsg.warn(f'Could not find "Crux version" line in output:\n{output[:400]}')
        return None
    return _parse_version(match.group(1))

# -- _get_crux_version: returns a tuple of ints corresponding to parsed version number
def _get_trfp_version(trfp_path: Path) -> Optional[tuple[int, ...]]:
    '''
    Run ThermoRawFileParser with no arguments and parse the version from
    its output.  On non-Windows, direct invocation is attempted first
    (works for native builds >= 2.0.0); if that yields no parseable
    version, falls back to invoking via Mono.

    Example output:
        1.4.5
    '''
    def _run(cmd: list[str]) -> Optional[str]:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            return (result.stdout + result.stderr).strip()
        except Exception:
            return None
    # Try direct invocation first (works for native builds >= 2.0.0)
    output = _run([str(trfp_path), '--version'])
    if output is None or not re.search(r'\d+\.\d+', output):
        # Fall back to mono on non-Windows
        if platform.system() != 'Windows':
            mono = shutil.which('mono')
            if mono:
                output = _run([mono, str(trfp_path), '--version'])
    if output is None:
        return None
    return _parse_version(output)