'''
Defines shared fixtures and binary-availability guards for testing
'''

# -- Import external dependencies
import os, pytest, shutil
from pathlib import Path
from typing import Generator, Optional

# -- Define root directories external dependencies
TESTS_DIR = Path(__file__).parent
REPO_ROOT = TESTS_DIR.parent
BIN_DIR = REPO_ROOT / 'bin'

# -- Import internal dependencies
from tests.fixtures.generate_fixtures import generate_all, PROTEINS, TARGET_PEPTIDES, write_fasta, write_mzml

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
    return sorted(matches)[-1] if matches else None

@pytest.fixture(scope='session')
def crux_bin() -> Path:
    '''
    Returns the path to the Crux binary, skipping the requesting test (and any that depend on it) if Crux is absent
    '''
    path = _find_crux(BIN_DIR)
    if path is None:
        pytest.skip(
            f'Crux binary not found under {BIN_DIR}. Run `comms setup crux` to install it, then re-run the tests.'
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
            f'ThermoRawFileParser.exe not found under {BIN_DIR}. Run `comms setup trfp` to install it, then re-run the tests.'
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
        'sample_id\traw_file\ttreatment\treplicate\tbatch\n'
        'S1\tsynthetic.mzML\tCONTROL\t1\tA\n'
        'S2\tsynthetic.mzML\tTREATMENT\t1\tA\n'
    )
    p = tmp_path / 'sample_sheet.tsv'
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
        'sample_id\traw_file\ttreatment\treplicate\n'
        'S1\tsynthetic.mzML\tCONTROL\t1\n'
        'S1\tsynthetic.mzML\tTREATMENT\t1\n'
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
