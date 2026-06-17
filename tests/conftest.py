'''
Defines shared fixtures and binary-availability guards for testing
'''

# -- Import external dependencies
import os, pytest
from pathlib import Path
from PySide6.QtCore import qInstallMessageHandler, QtMsgType
from typing import Optional

# -- Define root directories external dependencies
TESTS_DIR = Path(__file__).parent
REPO_ROOT = TESTS_DIR.parent
BIN_DIR = REPO_ROOT / 'bin'

# -- Import internal dependencies
from tests.fixtures.generate_fixtures import generate_all, write_fasta, write_mzml

# -- Set environment variable for offscreen Qt platform
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

# -- Register custom pytest markers
def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        'markers',
        'crux: mark test as requiring the Crux binary (skip if absent)',
    )
    config.addinivalue_line(
        'markers',
        'trfp: mark test as requiring ThermoRawFileParser (skip if absent)',
    )


# -- Define session-scoped binary fixtures
def _find_crux(bin_dir: Path) -> Optional[Path]:
    '''Mirrors comms.utils.crux.findCrux'''
    matches = list(bin_dir.glob('crux*/bin/crux'))
    return sorted(matches)[-1] if matches else None

def _find_trfp(bin_dir: Path) -> Optional[Path]:
    '''Mirrors comms.utils.trfp.findTRFP'''
    matches = list(bin_dir.glob('*/ThermoRawFileParser.exe'))
    matches += list(bin_dir.glob('*/ThermoRawFileParser'))
    return sorted(matches)[-1] if matches else None

@pytest.fixture(scope='session')
def crux_bin() -> Path:
    '''
    Returns the path to the Crux binary, skipping the requesting test (and any that depend on it) if Crux is absent
    '''
    path = _find_crux(BIN_DIR)
    if path is None:
        pytest.skip(
            f'Crux binary not found under {BIN_DIR}. Install it, then re-run the tests.'
        )
    return path

@pytest.fixture(scope='session')
def trfp_exe() -> Path:
    '''
    Returns the path to ThermoRawFileParser.exe, skipping the requesting test (and any that depend on it) if TRFP is absent
    '''
    path = _find_trfp(BIN_DIR)
    if path is None:
        pytest.skip(
            f'ThermoRawFileParser.exe not found under {BIN_DIR}. Install it, then re-run the tests.'
        )
    return path

# -- Create synthetic fixture files
@pytest.fixture()
def synthetic_fasta(tmp_path: Path) -> Path:
    '''Write the synthetic proteome FASTA to a temp directory and return its path'''
    return write_fasta(tmp_path / 'synthetic_proteome.fasta')

@pytest.fixture()
def synthetic_mzml(tmp_path: Path) -> Path:
    '''Write the synthetic mzML to a temp directory and return its path'''
    return write_mzml(tmp_path / 'synthetic.mzML')

@pytest.fixture()
def synthetic_fixtures(tmp_path: Path) -> tuple[Path, Path]:
    '''
    Write both synthetic fixture files into the same temp directory, returning (fasta_path, mzml_path).
    '''
    return generate_all(tmp_path)

# -- Create sample sheet fixtures
@pytest.fixture()
def valid_sample_sheet(tmp_path: Path) -> Path:
    '''
    Write a minimal valid comMS sample sheet (TSV) and return its path
    '''
    content = (
        'sample_id\traw_file\ttreatment\tfraction\treplicate\tbatch\n'
        'S1\tsynthetic.mzML\tCONTROL\tWCL\t1\tA\n'
        'S2\tsynthetic.mzML\tTREATMENT\tWCL\t1\tA\n'
    )
    p = tmp_path / 'sample_sheet.tsv'
    p.write_text(content)
    return p

@pytest.fixture()
def valid_sample_sheet_single_fraction(tmp_path: Path) -> Path:
    '''
    Write a minimal sample sheet with a single fraction (WCL) and return its path
    '''
    content = (
        'sample_id\traw_file\ttreatment\tfraction\treplicate\n'
        'S1\tsample_mock_wcl_1.RAW\tMOCK\tWCL\t1\n'
        'S2\tsample_treat_wcl_1.RAW\tTREAT\tWCL\t1\n'
    )
    p = tmp_path / 'sample_sheet_single_fraction.tsv'
    p.write_text(content)
    return p

@pytest.fixture()
def valid_sample_sheet_multiple_fractions(tmp_path: Path) -> Path:
    '''
    Write a minimal sample sheet with three fractions (WCL, ECF, PUR), two treatments, and one
    replicate each and return its path
    '''
    content = (
        'sample_id\traw_file\ttreatment\tfraction\treplicate\tbatch\n'
        'S1\tsample_mock_wcl_1.RAW\tMOCK\tWCL\t1\tA\n'
        'S2\tsample_treat_wcl_1.RAW\tTREAT\tWCL\t1\tA\n'
        'S3\tsample_mock_ecf_1.RAW\tMOCK\tECF\t1\tA\n'
        'S4\tsample_treat_ecf_1.RAW\tTREAT\tECF\t1\tA\n'
        'S5\tsample_mock_pur_1.RAW\tMOCK\tPUR\t1\tA\n'
        'S6\tsample_treat_pur_1.RAW\tTREAT\tPUR\t1\tA\n'
    )
    p = tmp_path / 'sample_sheet_multiple_fractions.tsv'
    p.write_text(content)
    return p

@pytest.fixture()
def sample_sheet_missing_col(tmp_path: Path) -> Path:
    '''Sample sheet missing the required `treatment` column'''
    content = (
        'sample_id\traw_file\treplicate\n'
        'S1\tsynthetic.mzML\t1\n'
    )
    p = tmp_path / 'bad_sample_sheet.tsv'
    p.write_text(content)
    return p

@pytest.fixture()
def sample_sheet_duplicate_ids(tmp_path: Path) -> Path:
    '''Sample sheet with duplicate sample_id values'''
    content = (
        'sample_id\traw_file\ttreatment\tfraction\treplicate\n'
        'S1\tsynthetic.mzML\tCONTROL\tWCL\t1\n'
        'S1\tsynthetic.mzML\tTREATMENT\tWCL\t1\n'
    )
    p = tmp_path / 'dup_sample_sheet.tsv'
    p.write_text(content)
    return p

# -- Define isolated user config fixtures
@pytest.fixture()
def isolated_config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    '''
    Monkeypatches `userConfigPath` in settings and config modules so tests don't modift actual OS config directory, returning the temp config directory
    '''
    config_dir = tmp_path / 'config'
    config_dir.mkdir()
    fake_config_path = config_dir / 'config.toml'
    def _fake_user_config_path() -> Path:
        return fake_config_path
    monkeypatch.setattr('comms.utils.settings.userConfigPath', _fake_user_config_path)
    monkeypatch.setattr('comms.commands.config.userConfigPath', _fake_user_config_path)
    return config_dir

# -- Define synthetic percolator results
@pytest.fixture()
def synthetic_percolator_results(tmp_path):
    '''
    Write a minimal synthetic assign-confidence PSM file in the per-organism subdirectory structure produced by run_rescore round 2, bypassing the need to run Percolator and assign-confidence on synthetic data (which does not provide enough PSMs for Percolator to converge)
    '''
    rescore_dir = tmp_path / 'comms' / 'results' / 'rescore'
    rescore_dir.mkdir(parents=True)
    psm_content = (
        'PSMId\tscore\tq-value\tposterior_error_prob\tpeptide\tproteinIds\n'
        'synthetic_2_2_1\t1.5\t0.01\t0.001\tK.ACDEFGHIK.L\tSP|PROT1|GENE1\n'
        'synthetic_3_2_1\t1.3\t0.01\t0.002\tR.LMNPQR.S\tSP|PROT1|GENE1\n'
        'synthetic_4_2_1\t1.2\t0.01\t0.003\tK.SAMPLEK.T\tSP|PROT2|GENE2\n'
    )
    # Per-organism subdirectory with assign-confidence output
    org_dir = rescore_dir / 'EUK'
    org_dir.mkdir()
    (org_dir / 'synthetic.EUK.assign-confidence.target.txt').write_text(psm_content)
    return rescore_dir

@pytest.fixture()
def multi_fraction_psm_dir(tmp_path: Path) -> Path:
    '''
    Write synthetic Percolator PSM files for three fractions (WCL, AWF, EV),
    two samples per fraction, matching the filenames in
    valid_multi_fraction_sample_sheet. Returns the directory path.
    '''
    rescore_dir = tmp_path / 'comms' / 'results' / 'rescore'
    rescore_dir.mkdir(parents=True)
    psm_header = 'PSMId\tscore\tq-value\tposterior_error_prob\tpeptide\tproteinIds\n'
    psm_row = 'synthetic_1\t1.5\t0.01\t0.001\tK.ACDEFGHIK.L\tSP|PROT1|GENE1\n'
    stems = [
        'sample_mock_wcl_1',
        'sample_treat_wcl_1',
        'sample_mock_ecf_1',
        'sample_treat_ecf_1',
        'sample_mock_pur_1',
        'sample_treat_pur_1',
    ]
    for stem in stems:
        psm_file = rescore_dir / f'{stem}.percolator.target.psms.txt'
        psm_file.write_text(psm_header + psm_row)
    return rescore_dir

@pytest.fixture()
def single_fraction_psm_dir(tmp_path: Path) -> Path:
    '''
    Write synthetic Percolator PSM files for a single fraction (WCL), matching
    the filenames in valid_sample_sheet_single_fraction.
    '''
    rescore_dir = tmp_path / 'comms' / 'results' / 'rescore'
    rescore_dir.mkdir(parents=True)
    psm_header = 'PSMId\tscore\tq-value\tposterior_error_prob\tpeptide\tproteinIds\n'
    psm_row = 'synthetic_1\t1.5\t0.01\t0.001\tK.ACDEFGHIK.L\tSP|PROT1|GENE1\n'
    for stem in ('sample_mock_wcl_1', 'sample_treat_wcl_1'):
        psm_file = rescore_dir / f'{stem}.percolator.target.psms.txt'
        psm_file.write_text(psm_header + psm_row)
    return rescore_dir

# -- Define session-scoped QApplication for GUI tests
@pytest.fixture(scope='session')
def qapp():
    '''
    Return a single QApplication for the test session, using the offscreen platform to avoid needing a display
    '''
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app

def _qt_message_handler(mode: QtMsgType, context, message: str) -> None:
    '''
    Custom Qt message handler to suppress known harmless warnings from the offscreen platform plugin that cannot perform operations (such as keyboard grabs) which require a real display; all other messages are forwarded to Qt's default behaviour (stderr)
    '''
    _SUPPRESSED = {
        'does not support grabbing the keyboard',
        'does not support grabbing the mouse',
    }
    if any(fragment in message for fragment in _SUPPRESSED):
        return
    # For everything else, replicate Qt's default: print to stderr.
    import sys
    print(message, file=sys.stderr)

qInstallMessageHandler(_qt_message_handler)