'''
comMS motif extension: MEME suite binary discovery and subprocess wrapper
'''

# -- Import external dependencies
import platform, re, shutil, subprocess
from dataclasses import dataclass
from pathlib import Path

# -- Import internal comMS logMsg class
from comms.utils.log import logMsg

# -- Define variables for MEME
_MEME_MIN_VERSION = (5, 0, 0)   # STREME introduced in MEME Suite 5.0.0
_MEME_TOOLS = ('meme', 'streme', 'fimo', 'ame')

# -- Define custom error classes for MEME not being found or being too old
class MemeNotFoundError(RuntimeError):
    '''No usable MEME Suite installation could be located'''

class MemeVersionError(RuntimeError):
    '''The installed MEME Suite is too old for the requested tool'''

# -- Define dataclass MemeInstall to hold information about MEME's installation
@dataclass(frozen=True)
class MemeInstall:
    bin_dir: Path
    version: tuple[int, int, int]
    def tool(self, name: str) -> Path:
        if name not in _MEME_TOOLS:
            raise ValueError(f'Unknown MEME tool: {name!r}')
        path = self.bin_dir / name
        if not path.exists():
            raise MemeNotFoundError(f'MEME tool {name!r} not found in {self.bin_dir}')
        return path
    @property
    def version_str(self) -> str:
        return ".".join(str(n) for n in self.version)

# ===================================
# MEME suite binary discovery
# ===================================
# -- _candidate_bin_dirs: returns a list of Paths that are plausible directories to have MEME binary in
def _candidate_bin_dirs(hint: Path | None) -> list[Path]:
    candidates: list[Path] = []
    if hint is not None:
        hint = hint.expanduser()
        candidates.append(hint)
        candidates.append(hint / 'bin')
        candidates.extend(p.parent for p in hint.glob('meme-*/bin/meme'))
    on_path = shutil.which('streme') or shutil.which('meme')
    if on_path:
        candidates.append(Path(on_path).parent)
    seen: set[Path] = set()
    unique: list[Path] = []
    for c in candidates:
        if not c.is_dir():
            continue
        rc = c.resolve()
        if rc not in seen:
            seen.add(rc)
            unique.append(rc)
    return unique

# -- _parse_version: returns a tuple of ints corresponding to parsed MEME suite version
def _parse_version(text: str) -> tuple[int, int, int] | None:
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", text)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None

# -- _query_version: returns either a tuple of ints (from _parse_version) or None (if MEME not found)
def _query_version(meme_bin: Path) -> tuple[int, int, int] | None:
    try:
        result = subprocess.run(
            [str(meme_bin), '-version'],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return _parse_version(result.stdout) or _parse_version(result.stderr)

# find_meme: returns a MemeInstall after locaitng MEME installation
def find_meme(hint: Path | None = None) -> MemeInstall:
    if platform.system() == 'Windows':
        raise MemeNotFoundError('MEME Suite is not supported natively on Windows. Run comms under WSL2 with MEME Suite installed there. See https://meme-suite.org/.')
    for bin_dir in _candidate_bin_dirs(hint):
        meme_bin = bin_dir / 'meme'
        if not meme_bin.exists():
            continue
        version = _query_version(meme_bin)
        if version is None:
            logMsg.warn(f'Found MEME at {meme_bin} but could not read its version')
            continue
        install = MemeInstall(bin_dir=bin_dir, version=version)
        logMsg.info(f'Using MEME Suite {install.version_str} from {bin_dir}')
        return install
    raise MemeNotFoundError(
        'No MEME Suite installation found in default paths, ensure it is installed and pass --meme-dir')

# require_streme: returns a Path to MEME version able to run STREME (i.e. ≥ 5.0.0)
def require_streme(install: MemeInstall) -> Path:
    if install.version < _MEME_MIN_VERSION:
        minimum = '.'.join(str(n) for n in _MEME_MIN_VERSION)
        raise MemeVersionError(f'STREME requires MEME Suite >= {minimum} but found {install.version_str}, use --algorithm meme, or upgrade MEME Suite')
    return install.tool("streme")

# ===================================
# MEME suite run wrappers
# ===================================
# -- _run: returns None, but runs the specified arguments via subprocess and checks if return code is 0
def _run(args: list[str], label: str) -> None:
    logMsg.info(f'Running {label}: {' '.join(args)}')
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        logMsg.error('{label} failed (exit {result.returncode}): {result.stderr}')
        raise RuntimeError(f'{label} exited with code {result.returncode}')