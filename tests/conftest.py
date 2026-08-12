'''
Defines shared fixtures and binary-availability guards for testing
'''

# -- Set environment variable for offscreen Qt platform
import os
os.environ['QT_QPA_PLATFORM'] = 'minimal'

# -- Import external dependencies
import os, pytest
from pathlib import Path
from PySide6.QtCore import qInstallMessageHandler, QtMsgType
from typing import Optional


# -- Define bin directory for tests requiring Crux/ThermoRawFileParser
BIN_DIR = Path(__file__).parent / 'bin'

# -- Point comMS at the test bin/ directory for the whole session
@pytest.fixture(autouse=True)
def _comms_bin_dir_env(monkeypatch):
    monkeypatch.setenv('COMMS_BIN_DIR', str(BIN_DIR))

# -- Import internal dependencies
from tests.fixtures.generate_fixtures import generate_all, write_fasta, write_mzml

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
def sample_sheet_factory(tmp_path: Path):
    '''
    Returns a function that writes a minimal comMS sample sheet (TSV) with the
    given fractions (two treatments, one replicate each, optional batch column)
    and returns its path.
    '''
    def _make(fractions: list[str] = ('WCL',), batch: bool = True) -> Path:
        columns = ['sample_id', 'raw_file', 'treatment', 'fraction', 'replicate']
        if batch:
            columns.append('batch')
        lines = ['\t'.join(columns)]
        for i, fraction in enumerate(fractions):
            for j, treatment in enumerate(('MOCK', 'TREAT')):
                sample_id = f'S{i * 2 + j + 1}'
                raw_file = f'sample_{treatment.lower()}_{fraction.lower()}_1.RAW'
                row = [sample_id, raw_file, treatment, fraction, '1']
                if batch:
                    row.append('A')
                lines.append('\t'.join(row))
        p = tmp_path / f'sample_sheet_{"_".join(fractions).lower()}.tsv'
        p.write_text('\n'.join(lines) + '\n')
        return p
    return _make

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
    Monkeypatches `globalConfigPath` in settings and config modules so tests don't modift actual OS config directory, returning the temp config directory
    '''
    config_dir = tmp_path / 'config'
    config_dir.mkdir()
    fake_config_path = config_dir / 'config.toml'
    def _fake_user_config_path() -> Path:
        return fake_config_path
    monkeypatch.setattr('comms.utils.settings.globalConfigPath', _fake_user_config_path)
    monkeypatch.setattr('comms.commands.config.globalConfigPath', _fake_user_config_path)
    monkeypatch.setattr('comms.commands.uninstall.globalConfigPath', _fake_user_config_path)
    return config_dir

# -- Define synthetic percolator results
@pytest.fixture()
def synthetic_percolator_results(tmp_path):
    '''
    Write a minimal synthetic Percolator PSM file in the per-organism subdirectory structure produced by run_rescore round 2, bypassing the need to run Percolator
    on synthetic data (which does not provide enough PSMs for Percolator to converge)
    '''
    rescore_dir = tmp_path / 'comms' / 'results' / 'rescore'
    rescore_dir.mkdir(parents=True)
    psm_content = (
        'PSMId\tscore\tq-value\tposterior_error_prob\tpeptide\tproteinIds\n'
        'synthetic_2_2_1\t1.5\t0.01\t0.001\tK.ACDEFGHIK.L\tSP|PROT1|GENE1\n'
        'synthetic_3_2_1\t1.3\t0.01\t0.002\tR.LMNPQR.S\tSP|PROT1|GENE1\n'
        'synthetic_4_2_1\t1.2\t0.01\t0.003\tK.SAMPLEK.T\tSP|PROT2|GENE2\n'
    )
    org_dir = rescore_dir / 'EUK'
    org_dir.mkdir()
    (org_dir / 'synthetic.EUK.percolator.target.psms.txt').write_text(psm_content)
    return rescore_dir

@pytest.fixture()
def psm_dir_factory(tmp_path: Path):
    '''
    Returns a function that writes one synthetic Percolator PSM file per given
    stem under comms/results/rescore/, and returns that directory.
    '''
    psm_header = 'PSMId\tscore\tq-value\tposterior_error_prob\tpeptide\tproteinIds\n'
    psm_row = 'synthetic_1\t1.5\t0.01\t0.001\tK.ACDEFGHIK.L\tSP|PROT1|GENE1\n'

    def _make(stems: list[str]) -> Path:
        rescore_dir = tmp_path / 'comms' / 'results' / 'rescore'
        rescore_dir.mkdir(parents=True, exist_ok=True)
        for stem in stems:
            (rescore_dir / f'{stem}.percolator.target.psms.txt').write_text(psm_header + psm_row)
        return rescore_dir
    return _make

# -- Define session-scoped QApplication for GUI tests
@pytest.fixture(scope='session')
def qapp():
    '''
    Return a single QApplication for the test session, using the offscreen platform to avoid needing a display
    '''
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([''])
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

# -- Add a function-scoped experiment context for most tests
@pytest.fixture()
def experiment_ctx(tmp_path, isolated_config_dir):
    '''A bare ExperimentContext rooted at tmp_path (no experiment.toml)'''
    from comms.utils.context import ExperimentContext
    return ExperimentContext.resolve(tmp_path)

# -- Add a fixture for integration-layer tests
@pytest.fixture()
def experiment_builder(tmp_path: Path, isolated_config_dir, sample_sheet_factory, psm_dir_factory):
    '''
    Compose a comms/ directory from only the pieces a test asks for.
    Usage: root, ctx = experiment_builder.with_sample_sheet().with_stage_output('rescore').build()
    '''
    import tomli_w
    from comms.utils.context import ExperimentContext

    class _Builder:
        def __init__(self):
            self._metadata: dict = {'experiment': {'name': 'exp', 'updated': '2026-01-01T00:00:00+00:00'}}
            self._sample_sheet_path: Path | None = None

        def with_sample_sheet(self, fractions=('WCL',), batch=True):
            self._sample_sheet_path = sample_sheet_factory(list(fractions), batch=batch)
            self._metadata.setdefault('files', {})['sample_sheet'] = str(self._sample_sheet_path)
            return self

        def with_stage_output(self, stage: str, files: list[str] | None = None):
            if stage in ('rescore',):
                psm_dir_factory(files or ['sample_mock_wcl_1', 'sample_treat_wcl_1'])
            else:
                out_dir = tmp_path / 'comms' / 'results' / stage
                out_dir.mkdir(parents=True, exist_ok=True)
                for name in (files or [f'placeholder.{stage}.txt']):
                    (out_dir / name).write_text('')
            return self

        def with_metadata(self, **kwargs):
            for section, values in kwargs.items():
                self._metadata.setdefault(section, {}).update(values)
            return self

        def build(self):
            comms_dir = tmp_path / 'comms'
            comms_dir.mkdir(parents=True, exist_ok=True)
            with (comms_dir / 'experiment.toml').open('wb') as f:
                tomli_w.dump(self._metadata, f)
            ctx = ExperimentContext.resolve(tmp_path)
            return tmp_path, ctx

    return _Builder()