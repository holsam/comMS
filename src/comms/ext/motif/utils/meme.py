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

# -- Define dataclass DiscoverParams to hold comms motif discover command config
@dataclass(frozen=True)
class DiscoverParams:
    algorithm: str = 'streme'
    min_width: int = 6
    max_width: int = 15
    n_motifs: int = 5
    evalue_threshold: float = 0.05
    seed: int = 42

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

# -- run_streme: returns Path to output directory after running differential (foreground vs background) discovery with STREME 
def run_streme(
    install: MemeInstall,
    foreground_fa: Path,
    background_fa: Path,
    out_dir: Path,
    params: DiscoverParams,
) -> Path:
    streme = require_streme(install)
    out_dir.mkdir(parents=True, exist_ok=True)
    args = [
        str(streme),
        '--protein',
        '--p', str(foreground_fa),
        '--n', str(background_fa),
        '--minw', str(params.min_width),
        '--maxw', str(params.max_width),
        '--nmotifs', str(params.n_motifs),
        '--evalue',                                  # threshold below is an E-value
        '--thresh', str(params.evalue_threshold),
        '--seed', str(params.seed),
        '--oc', str(out_dir),                        # --oc overwrites; --o refuses
    ]
    _run(args, 'STREME')
    if not (out_dir / 'streme.txt').exists():
        raise RuntimeError(f'STREME finished but {out_dir / 'streme.txt'} was not produced')
    return out_dir

# -- run_meme: returns Path to output directory after running differential (foreground vs background) discovery with MEME
def run_meme(
    install: MemeInstall,
    foreground_fa: Path,
    background_fa: Path,
    out_dir: Path,
    params: DiscoverParams,
) -> Path:
    meme = install.tool('meme')
    out_dir.mkdir(parents=True, exist_ok=True)
    args = [
        str(meme),
        str(foreground_fa),
        '-protein',
        '-oc', str(out_dir),
        '-objfun', 'de',
        '-neg', str(background_fa),
        '-minw', str(params.min_width),
        '-maxw', str(params.max_width),
        '-nmotifs', str(params.n_motifs),
        '-evt', str(params.evalue_threshold),
        '-seed', str(params.seed),
        '-nostatus',
    ]
    _run(args, 'MEME')
    if not (out_dir / 'meme.txt').exists():
        raise RuntimeError(f'MEME finished but {out_dir / 'meme.txt'} was not produced')
    return out_dir

# ===================================
# MEME parsing
# ===================================
# -- Define dataclass ParsedMotif to hold information about a parsed motif
@dataclass
class ParsedMotif:
    motif_id: str
    alt: str
    width: int
    nsites: int
    evalue: str
    allowed: list[set[str]] # per-position residues with prob >= 0.2

# -- parse_minimal_meme: return list of ParsedMotif, from a minimal-MEME file 
def parse_minimal_meme(meme_txt: Path, prob_cut: float = 0.2) -> list[ParsedMotif]:
    lines = meme_txt.read_text().splitlines()
    alphabet: list[str] = []
    for line in lines:
        if line.startswith('ALPHABET'):
            payload = re.sub(r"ALPHABET=?\s*", '', line).strip()
            alphabet = [c for c in payload if c.isalpha()]
            break
    motifs: list[ParsedMotif] = []
    i = 0
    while i < len(lines):
        if lines[i].startswith('MOTIF'):
            header = lines[i].split()
            motif_id = header[1]
            alt = header[2] if len(header) > 2 else ''
            j = i + 1
            while j < len(lines) and 'letter-probability matrix' not in lines[j]:
                j += 1
            meta = lines[j]
            width = int(re.search(r"w=\s*(\d+)", meta).group(1))
            nsites_m = re.search(r"nsites=\s*(\d+)", meta)
            evalue_m = re.search(r"E=\s*(\S+)", meta)
            allowed: list[set[str]] = []
            for row in lines[j + 1: j + 1 + width]:
                probs = [float(x) for x in row.split()]
                allowed.append({alphabet[k] for k, p in enumerate(probs) if p >= prob_cut})
            motifs.append(ParsedMotif(
                motif_id=motif_id,
                alt=alt,
                width=width,
                nsites=int(nsites_m.group(1)) if nsites_m else 0,
                evalue=evalue_m.group(1) if evalue_m else 'NA',
                allowed=allowed,
            ))
            i = j + width
        i += 1
    return motifs

# -- _motif_regex: returns a regex pattern from a given motif
def _motif_regex(motif: ParsedMotif) -> re.Pattern:
    parts = []
    for residues in motif.allowed:
        parts.append('.' if not residues else f'[{''.join(sorted(residues))}]')
    return re.compile(''.join(parts))

# -- scan_indicative_sites: returns list of dictionaries that correspond to indicative motif hits by matching per-position allowed-residue regex against foreground protein set
def scan_indicative_sites(
    motifs: list[ParsedMotif],
    sequences: dict[str, str],
) -> list[dict]:
    rows: list[dict] = []
    for motif in motifs:
        pattern = _motif_regex(motif)
        for protein_id, seq in sequences.items():
            for match in pattern.finditer(seq):
                rows.append({
                    'motif_id': motif.motif_id,
                    'protein_id': protein_id,
                    'start': match.start() + 1,   # first amino acid = position 1
                    'width': motif.width,
                })
    return rows