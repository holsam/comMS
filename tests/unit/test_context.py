'''
Unit tests for src/comms/utils/context.py
'''

# -- Import external dependencies
import tomli_w, pytest
from pathlib import Path

# -- Import functions under test
from comms.utils.context import ExperimentContext, _normalise_dirs
from comms.utils.settings import loadDefaultConfig

# _write_experiment: creates a mock experiment directory to use in tests
def _write_experiment(comms_dir: Path, *, bin_dir: str | None = None) -> None:
    comms_dir.mkdir(parents=True, exist_ok=True)
    meta = {'experiment': {'name': 'exp', 'updated': '2026-01-01T00:00:00+00:00'}}
    if bin_dir is not None:
        meta['experiment']['bin_dir'] = bin_dir
    with (comms_dir / 'experiment.toml').open('wb') as f:
        tomli_w.dump(meta, f)

# -- Define tests for _normalise_dirs function
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

# -- Define tests for resolve method of ExperimentContext
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