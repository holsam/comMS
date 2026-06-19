'''
Unit tests for src/comms/utils/context.py
'''

# -- Import external dependencies
import tomli_w, pytest
from pathlib import Path
from unittest.mock import MagicMock

# -- Import functions under test
from comms.utils.context import (
    ExperimentContext,
    _check_files, _choose, _normalise_dirs,
    resolve_data_files, resolve_database, resolve_mzml_files,
    resolve_organism_prefix, resolve_sample_sheet,
    results_dir,
)
from comms.utils.settings import loadDefaultConfig

# ===========================================================================
# Shared helpers
# ===========================================================================
def _write_experiment(comms_dir: Path, *, bin_dir: str | None = None) -> None:
    comms_dir.mkdir(parents=True, exist_ok=True)
    meta = {'experiment': {'name': 'exp', 'updated': '2026-01-01T00:00:00+00:00'}}
    if bin_dir is not None:
        meta['experiment']['bin_dir'] = bin_dir
    with (comms_dir / 'experiment.toml').open('wb') as f:
        tomli_w.dump(meta, f)

def _make_ctx(tmp_path: Path, metadata: dict | None = None) -> ExperimentContext:
    '''Return a minimal ExperimentContext with bundled-default config.'''
    return ExperimentContext(
        root=tmp_path,
        comms_dir=tmp_path / 'comms',
        config=loadDefaultConfig(),
        config_source='bundled defaults',
        bin_dir=None,
        metadata=metadata or {},
    )

# -- Ensure logMsg is initialised for every test so warn/error calls don't no-op
@pytest.fixture(autouse=True)
def setup_logger():
    from comms.utils.log import logMsg
    logMsg('context')
    yield

# ===========================================================================
# _normalise_dirs
# ===========================================================================
class TestNormaliseDirs:
    def test_plain_root_appends_comms(self, tmp_path):
        root, comms = _normalise_dirs(tmp_path)
        assert root == tmp_path
        assert comms == tmp_path / 'comms'

    def test_comms_dir_passed_directly(self, tmp_path):
        comms = tmp_path / 'comms'
        comms.mkdir()
        root, resolved = _normalise_dirs(comms)
        assert root == tmp_path
        assert resolved == comms

    def test_inner_dir_with_experiment_toml(self, tmp_path):
        inner = tmp_path / 'run1'
        inner.mkdir()
        (inner / 'experiment.toml').write_text('')
        root, resolved = _normalise_dirs(inner)
        assert root == tmp_path
        assert resolved == inner

# ===========================================================================
# ExperimentContext.resolve
# ===========================================================================
class TestResolve:
    def test_no_experiment_falls_back_to_default(self, tmp_path, isolated_config_dir):
        ctx = ExperimentContext.resolve(tmp_path)
        assert ctx.config == loadDefaultConfig()
        assert ctx.bin_dir is None
        assert ctx.root == tmp_path

    def test_local_config_preferred(self, tmp_path, isolated_config_dir):
        comms = tmp_path / 'comms'
        _write_experiment(comms)
        local = loadDefaultConfig()
        local['search']['threads'] = 99
        with (comms / 'config.toml').open('wb') as f:
            tomli_w.dump(local, f)
        ctx = ExperimentContext.resolve(tmp_path)
        assert ctx.config['search']['threads'] == 99
        assert ctx.config_source.startswith('local')

    def test_bin_dir_read_from_metadata(self, tmp_path, isolated_config_dir):
        comms = tmp_path / 'comms'
        _write_experiment(comms, bin_dir='/opt/comms/bin')
        ctx = ExperimentContext.resolve(tmp_path)
        assert ctx.bin_dir == Path('/opt/comms/bin')

# ===========================================================================
# ExperimentContext stored-input properties (data_files, database, sample_sheet, organism_prefix, ref_info, cont_csv)
# ===========================================================================
class TestExperimentContextProperties:
    '''ExperimentContext properties for stored inputs from [files] and [report]'''
    def test_data_files_returns_list_when_present(self, tmp_path):
        files = [tmp_path / f'f{i}.RAW' for i in range(2)]
        for f in files:
            f.touch()
        ctx = _make_ctx(tmp_path, metadata={'files': {'data': [str(f) for f in files]}})
        result = ctx.data_files
        assert len(result) == 2
        assert all(isinstance(f, Path) for f in result)

    def test_data_files_returns_empty_list_when_absent(self, tmp_path):
        ctx = _make_ctx(tmp_path)
        assert ctx.data_files == []

    def test_database_returns_path_when_present(self, tmp_path):
        db = tmp_path / 'db.fasta'
        db.touch()
        ctx = _make_ctx(tmp_path, metadata={'files': {'database': str(db)}})
        assert ctx.database == db

    def test_database_returns_none_when_absent(self, tmp_path):
        ctx = _make_ctx(tmp_path)
        assert ctx.database is None

    def test_sample_sheet_returns_path_when_present(self, tmp_path):
        ss = tmp_path / 'samples.csv'
        ss.touch()
        ctx = _make_ctx(tmp_path, metadata={'files': {'sample_sheet': str(ss)}})
        assert ctx.sample_sheet == ss

    def test_sample_sheet_returns_none_when_absent(self, tmp_path):
        ctx = _make_ctx(tmp_path)
        assert ctx.sample_sheet is None

    def test_analysis_mode_returns_stored_string(self, experiment_ctx):
        experiment_ctx.metadata["experiment"] = {"analysis": "single"}
        assert experiment_ctx.analysis_mode == 'single'

    def test_analysis_mode_returns_none_when_absent(self, experiment_ctx):
        assert experiment_ctx.analysis_mode is None

    def test_multispecies_true_when_mode_is_multi(self, experiment_ctx):
        experiment_ctx.metadata["experiment"] = {"analysis": "multi"}
        assert experiment_ctx.multispecies is True

    def test_multispecies_false_when_mode_is_single(self, experiment_ctx):
        experiment_ctx.metadata["experiment"] = {"analysis": "single"}
        assert experiment_ctx.multispecies is False

    def test_multispecies_fallback_to_config_organism(self, experiment_ctx, monkeypatch):
        monkeypatch.setitem(experiment_ctx.config, 'organism', {'EUK': 'TESTEUK'})
        assert experiment_ctx.multispecies is True

    def test_multispecies_false_when_no_mode_and_no_config_organism(self, experiment_ctx, monkeypatch):
        monkeypatch.setitem(experiment_ctx.config, 'organism', {})
        assert experiment_ctx.multispecies is False

    def test_organism_prefix_returns_string_when_present(self, tmp_path):
        ctx = _make_ctx(tmp_path, metadata={'report': {'organism_prefix': 'EUK'}})
        assert ctx.organism_prefix == 'EUK'

    def test_organism_prefix_returns_none_when_absent(self, tmp_path):
        ctx = _make_ctx(tmp_path)
        assert ctx.organism_prefix is None

    def test_ref_info_returns_path_when_present(self, tmp_path):
        ref = tmp_path / 'ref.txt'
        ref.touch()
        ctx = _make_ctx(tmp_path, metadata={'report': {'ref_info': str(ref)}})
        assert ctx.ref_info == ref

    def test_ref_info_returns_none_when_absent(self, tmp_path):
        ctx = _make_ctx(tmp_path)
        assert ctx.ref_info is None

    def test_cont_csv_returns_path_when_present(self, tmp_path):
        cont = tmp_path / 'cont.csv'
        cont.touch()
        ctx = _make_ctx(tmp_path, metadata={'report': {'cont_csv': str(cont)}})
        assert ctx.cont_csv == cont

    def test_cont_csv_returns_none_when_absent(self, tmp_path):
        ctx = _make_ctx(tmp_path)
        assert ctx.cont_csv is None

# ===========================================================================
# results_dir
# ===========================================================================
class TestResultsDir:
    def test_returns_canonical_path(self, tmp_path):
        ctx = MagicMock(spec=ExperimentContext, root=tmp_path)
        result = results_dir(ctx, 'search')
        assert result == tmp_path / 'comms/results/search'

    def test_independent_of_existence(self, tmp_path):
        ctx = MagicMock(spec=ExperimentContext, root=tmp_path)
        result = results_dir(ctx, 'rescore')
        assert not result.exists()
        assert result == tmp_path / 'comms/results/rescore'

# ===========================================================================
# _choose
# ===========================================================================
class TestChoose:
    def test_override_used_when_given(self, tmp_path):
        # When override is provided it is returned; warn-on-mismatch is
        # tested separately in test_override_warns_when_differs_from_stored.
        override = tmp_path / 'override.txt'
        override.touch()
        stored = tmp_path / 'stored.txt'
        stored.touch()
        result = _choose(stored, override, 'database', must_exist=False)
        assert result == override

    def test_override_warns_when_differs_from_stored(self, tmp_path, caplog):
        override = tmp_path / 'override.txt'
        override.touch()
        stored = tmp_path / 'stored.txt'
        stored.touch()
        caplog.clear()
        result = _choose(stored, override, 'database', must_exist=False)
        assert result == override
        assert 'database' in caplog.text
        assert 'override' in caplog.text.lower() or 'differ' in caplog.text.lower()

    def test_no_warning_when_override_matches_stored(self, tmp_path, caplog):
        path = tmp_path / 'same.txt'
        path.touch()
        caplog.clear()
        _choose(path, path, 'database', must_exist=False)
        assert 'database' not in caplog.text

    def test_stored_used_when_no_override(self, tmp_path):
        stored = tmp_path / 'stored.txt'
        stored.touch()
        result = _choose(stored, None, 'database', must_exist=False)
        assert result == stored

    def test_raises_when_neither_supplied(self):
        with pytest.raises(SystemExit):
            _choose(None, None, 'database', must_exist=False)

    def test_raises_when_resolved_path_missing_and_must_exist(self, tmp_path):
        stored = tmp_path / 'missing.txt'
        with pytest.raises(SystemExit):
            _choose(stored, None, 'database', must_exist=True)

    def test_returns_nonexistent_path_when_must_exist_false(self, tmp_path):
        stored = tmp_path / 'missing.txt'
        result = _choose(stored, None, 'database', must_exist=False)
        assert result == stored
        assert not result.exists()


# ===========================================================================
# _check_files
# ===========================================================================
class TestCheckFiles:
    def test_all_exist_returns_list_of_paths(self, tmp_path):
        files = [tmp_path / f'f{i}.txt' for i in range(3)]
        for f in files:
            f.touch()
        result = _check_files(files, 'data')
        assert result == [Path(f) for f in files]

    def test_one_missing_raises_systemexit(self, tmp_path):
        files = [
            tmp_path / 'exists.txt',
            tmp_path / 'missing.txt',
        ]
        files[0].touch()
        with pytest.raises(SystemExit):
            _check_files(files, 'data')

    def test_empty_list_returns_empty_list(self):
        result = _check_files([], 'data')
        assert result == []

    def test_returns_list_of_path_objects(self, tmp_path):
        f = tmp_path / 'f.txt'
        f.touch()
        result = _check_files([f], 'data')
        assert isinstance(result, list)
        assert all(isinstance(p, Path) for p in result)

# ===========================================================================
# resolve_data_files
# ===========================================================================
class TestResolveDataFiles:
    def test_returns_stored_list_when_no_override(self, tmp_path):
        files = [tmp_path / f'f{i}.RAW' for i in range(2)]
        for f in files:
            f.touch()
        ctx = MagicMock(spec=ExperimentContext, data_files=files)
        result = resolve_data_files(ctx, override=None)
        assert result == files

    def test_override_wins_and_warns_on_mismatch(self, tmp_path, caplog):
        stored_files = [tmp_path / 'stored.RAW']
        stored_files[0].touch()
        override_files = [tmp_path / 'override.RAW']
        override_files[0].touch()
        ctx = MagicMock(spec=ExperimentContext, data_files=stored_files)
        caplog.clear()
        result = resolve_data_files(ctx, override=override_files)
        assert result == override_files
        assert 'data' in caplog.text.lower()

    def test_raises_when_no_stored_and_no_override(self):
        ctx = MagicMock(spec=ExperimentContext, data_files=[])
        with pytest.raises(SystemExit):
            resolve_data_files(ctx, override=None)

    def test_raises_when_any_file_missing(self, tmp_path):
        files = [tmp_path / 'exists.RAW', tmp_path / 'missing.RAW']
        files[0].touch()
        ctx = MagicMock(spec=ExperimentContext, data_files=files)
        with pytest.raises(SystemExit):
            resolve_data_files(ctx, override=None)

    def test_returns_list_of_path_objects(self, tmp_path):
        files = [tmp_path / 'f.RAW']
        files[0].touch()
        ctx = MagicMock(spec=ExperimentContext, data_files=files)
        result = resolve_data_files(ctx, override=None)
        assert isinstance(result, list)
        assert all(isinstance(f, Path) for f in result)

# ===========================================================================
# resolve_mzml_files
# ===========================================================================
class TestResolveMzmlFiles:
    def test_override_returns_given_files(self, tmp_path):
        files = [tmp_path / f'f{i}.mzML' for i in range(2)]
        for f in files:
            f.touch()
        ctx = MagicMock(spec=ExperimentContext)
        result = resolve_mzml_files(ctx, override=files)
        assert result == files

    def test_override_checks_existence(self, tmp_path):
        files = [tmp_path / 'missing.mzML']
        ctx = MagicMock(spec=ExperimentContext)
        with pytest.raises(SystemExit):
            resolve_mzml_files(ctx, override=files)

    def test_globs_convert_results_when_no_override(self, tmp_path):
        ctx = MagicMock(spec=ExperimentContext, root=tmp_path)
        convert_dir = tmp_path / 'comms/results/convert'
        convert_dir.mkdir(parents=True)
        mzml_files = [convert_dir / f'f{i}.mzML' for i in range(2)]
        for f in mzml_files:
            f.touch()
        result = resolve_mzml_files(ctx, override=None)
        assert sorted(result) == sorted(mzml_files)

    def test_globs_both_mzml_and_mzml_gz(self, tmp_path):
        ctx = MagicMock(spec=ExperimentContext, root=tmp_path)
        convert_dir = tmp_path / 'comms/results/convert'
        convert_dir.mkdir(parents=True)
        mzml = convert_dir / 'f.mzML'
        mzml_gz = convert_dir / 'g.mzML.gz'
        mzml.touch()
        mzml_gz.touch()
        result = resolve_mzml_files(ctx, override=None)
        assert sorted([f.name for f in result]) == ['f.mzML', 'g.mzML.gz']

    def test_raises_when_no_files_found(self, tmp_path):
        ctx = MagicMock(spec=ExperimentContext, root=tmp_path)
        convert_dir = tmp_path / 'comms/results/convert'
        convert_dir.mkdir(parents=True)
        with pytest.raises(SystemExit):
            resolve_mzml_files(ctx, override=None)

# ===========================================================================
# resolve_database / resolve_sample_sheet
# ===========================================================================
class TestResolveSingleFileInputs:
    def test_resolve_database_returns_stored(self, tmp_path):
        db = tmp_path / 'db.fasta'
        db.touch()
        ctx = MagicMock(spec=ExperimentContext, database=db)
        result = resolve_database(ctx, override=None)
        assert result == db

    def test_resolve_database_override_wins(self, tmp_path, caplog):
        stored = tmp_path / 'stored.fasta'
        stored.touch()
        override = tmp_path / 'override.fasta'
        override.touch()
        ctx = MagicMock(spec=ExperimentContext, database=stored)
        caplog.clear()
        result = resolve_database(ctx, override=override)
        assert result == override
        assert 'database' in caplog.text.lower()

    def test_resolve_sample_sheet_returns_stored(self, tmp_path):
        ss = tmp_path / 'samples.csv'
        ss.touch()
        ctx = MagicMock(spec=ExperimentContext, sample_sheet=ss)
        result = resolve_sample_sheet(ctx, override=None)
        assert result == ss

    def test_resolve_sample_sheet_override_wins(self, tmp_path, caplog):
        stored = tmp_path / 'stored.csv'
        stored.touch()
        override = tmp_path / 'override.csv'
        override.touch()
        ctx = MagicMock(spec=ExperimentContext, sample_sheet=stored)
        caplog.clear()
        result = resolve_sample_sheet(ctx, override=override)
        assert result == override
        assert 'sample sheet' in caplog.text.lower()

    def test_resolve_raises_when_neither_supplied(self):
        ctx = MagicMock(spec=ExperimentContext, database=None)
        with pytest.raises(SystemExit):
            resolve_database(ctx, override=None)

    def test_resolve_raises_when_file_missing(self, tmp_path):
        ctx = MagicMock(spec=ExperimentContext, database=tmp_path / 'missing.fasta')
        with pytest.raises(SystemExit):
            resolve_database(ctx, override=None)

# ===========================================================================
# resolve_organism_prefix
# ===========================================================================
class TestResolveOrganismPrefix:
    def test_returns_stored_prefix(self):
        ctx = MagicMock(spec=ExperimentContext, organism_prefix='Mtrun')
        result = resolve_organism_prefix(ctx, override=None)
        assert result == 'Mtrun'

    def test_override_wins_and_warns(self, caplog):
        ctx = MagicMock(spec=ExperimentContext, organism_prefix='Stored')
        caplog.clear()
        result = resolve_organism_prefix(ctx, override='Override')
        assert result == 'Override'
        assert 'organism prefix' in caplog.text.lower()

    def test_raises_when_neither_available(self):
        ctx = MagicMock(spec=ExperimentContext, organism_prefix=None)
        with pytest.raises(SystemExit):
            resolve_organism_prefix(ctx, override=None)

    def test_returns_string(self):
        ctx = MagicMock(spec=ExperimentContext, organism_prefix='Prefix')
        result = resolve_organism_prefix(ctx, override=None)
        assert isinstance(result, str)