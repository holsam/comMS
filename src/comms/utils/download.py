'''
comMS download binaries utility functions
'''

# -- Import external dependencies
import platform, stat, tarfile, urllib.request, zipfile
from pathlib import Path
from typing import Optional
from urllib.error import URLError

# -- Import internal dependencies
from comms.utils.log import logMsg
from comms.utils.paths import repoBinDir

# -- Define constants
TRFP_DEFAULT_VERSION = "1.4.5"
CRUX_DEFAULT_VERSION = "4.2"

# -- Define ThermoRawFileParser GitHub release asset URL pattern
_TRFP_DOWNLOAD_URL = (
    f'https://github.com/compomics/ThermoRawFileParser'
    '/releases/download/v{version}/ThermoRawFileParser.zip'
)
_TRFP_ZIP_NAME = 'ThermoRawFileParser.zip'
_TRFP_EXE_NAME = 'ThermoRawFileParser.exe'

# -- Define Crux naming convention
_CRUX_DOWNLOAD_BASE = 'https://crux.ms/downloads'
_CRUX_PLATFORM_MAP: dict[tuple[str, str], tuple[str, str]] = {
    ('Linux',  'x86_64'):  ('Linux',  'x86_64'),
    ('Darwin', 'x86_64'):  ('Darwin', 'x86_64'),
    ('Darwin', 'arm64'):   ('Darwin', 'arm64'),
    ('Darwin', 'aarch64'): ('Darwin', 'arm64'),
}

# -- _resolve_bin_dir: return Path to bin directory
# =========================
def _resolve_bin_dir(override: Optional[Path] = None) -> Path:
    '''
    Uses override if supplied; otherwise falls back to config['tools']['bin_dir'], raises KeyError if neither is available.
    '''
    if override is not None:
        return override
    return repoBinDir()

# -- _detect_platform: returns tuple encoding system and machine
# =========================
def _detect_platform() -> tuple[str, str]:
    return platform.system(), platform.machine()

# -- _download_file: downloads URL to destination
# =========================
def _download_file(url: str, dest: Path) -> None:
    '''
    Progress logged at INFO level, raises urllib.error.URLError on network failure.
    '''
    logMsg.info(f'Fetching: {url}')
    try:
        urllib.request.urlretrieve(url, str(dest))
    except URLError as exc:
        raise URLError(f'Failed to download {url}: {exc}') from exc
    logMsg.debug(f'Saved to: {dest}')

# -- _set_executable: add the owner-execute bit to a file (no-op on Windows)
def _set_executable(path: Path) -> None:
    if platform.system() != 'Windows':
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

# -- download_thermorawfileparser: download and extract ThermoRawFileParser from the CompOmics GitHub releases page
def download_thermorawfileparser(
    version: str = TRFP_DEFAULT_VERSION,
    bin_dir: Optional[Path] = None,
    force: bool = False,
) -> Path:
    bin_dir_resolved = _resolve_bin_dir(bin_dir)
    logMsg.debug(f'Resolving bin directory: {bin_dir_resolved}')
    target_dir = bin_dir_resolved / f'ThermoRawFileParser-{version}'
    exe_path = target_dir / _TRFP_EXE_NAME
    if exe_path.exists() and not force:
        logMsg.warn(f'ThermoRawFileParser v{version} already present at {exe_path} — skipping (use --force to overwrite)')
        return exe_path
    target_dir.mkdir(parents=True, exist_ok=True)
    tmp_zip = target_dir / _TRFP_ZIP_NAME
    url = _TRFP_DOWNLOAD_URL.format(version=version)
    try:
        _download_file(url, tmp_zip)
    except URLError:
        tmp_zip.unlink(missing_ok=True)
        raise
    logMsg.info(f'Extracting ThermoRawFileParser archive to: {target_dir}')
    try:
        with zipfile.ZipFile(tmp_zip, 'r') as zf:
            zf.extractall(target_dir)
    except zipfile.BadZipFile as exc:
        raise RuntimeError(f'Downloaded file is not a valid zip archive: {tmp_zip}.') from exc
    finally:
        tmp_zip.unlink(missing_ok=True)
    if not exe_path.exists():
        raise RuntimeError(f'{_TRFP_EXE_NAME} not found in extracted archive at {target_dir}.')
    logMsg.info(f'ThermoRawFileParser v{version} ready at: {exe_path}')
    return exe_path

# -- download_crux: download and extract the Crux toolkit from crux.ms
def download_crux(
    version: str = CRUX_DEFAULT_VERSION,
    bin_dir: Optional[Path] = None,
    force: bool = False,
) -> Path:
    system, machine = _detect_platform()
    logMsg.debug(f'Detected platform: {system}/{machine}')
    # Windows: no tarball distribution available.
    if system == 'Windows':
        raise NotImplementedError(
            'Automated Crux download is not supported on Windows. Please install Crux manually from https://crux.ms/download.html and ensure the crux binary is available on your PATH, or use a Linux/macOS environment (e.g. WSL2 on Windows).'
        )
    platform_key = (system, machine)
    if platform_key not in _CRUX_PLATFORM_MAP:
        raise RuntimeError(
            f'Unrecognised platform/architecture: {system}/{machine}. Supported combinations: '
            + ', '.join(f'{s}/{m}' for s, m in _CRUX_PLATFORM_MAP)
            + '.'
        )
    crux_platform, crux_arch = _CRUX_PLATFORM_MAP[platform_key]
    tarball_stem = f'crux-{version}.{crux_platform}.{crux_arch}'
    tarball_name = f'{tarball_stem}.tar.gz'
    bin_dir_resolved = _resolve_bin_dir(bin_dir)
    target_dir = bin_dir_resolved / tarball_stem
    crux_bin = target_dir / 'bin' / 'crux'
    if crux_bin.exists() and not force:
        logMsg.warn(f'Crux v{version} already present at {crux_bin} — skipping (use --force to overwrite)')
        return crux_bin
    bin_dir_resolved.mkdir(parents=True, exist_ok=True)
    tmp_tar = bin_dir_resolved / tarball_name
    url = f'{_CRUX_DOWNLOAD_BASE}/{tarball_name}'
    try:
        _download_file(url, tmp_tar)
    except URLError:
        tmp_tar.unlink(missing_ok=True)
        raise
    logMsg.info(f'Extracting Crux archive to: {bin_dir_resolved}')
    try:
        with tarfile.open(tmp_tar, "r:gz") as tf:
            tf.extractall(bin_dir_resolved)
    except tarfile.TarError as exc:
        raise RuntimeError(
            f'Failed to extract Crux tarball {tmp_tar}: {exc}'
        ) from exc
    finally:
        tmp_tar.unlink(missing_ok=True)
    if not crux_bin.exists():
        raise RuntimeError(
            f'crux binary not found at expected path {crux_bin} after extraction. The archive layout may have changed for v{version}.'
        )
    _set_executable(crux_bin)
    logMsg.info(f'Crux v{version} ready at: {crux_bin}')
    return crux_bin