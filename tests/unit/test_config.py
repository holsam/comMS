'''
Unit tests for src/comms/commands/config.py and src/comms/utils/settings.py
'''

# -- Import external dependencies
import click, pytest, tomllib
from pathlib import Path

# -- Import internal functions
from comms.utils.settings import loadDefaultConfig, userConfigPath
from comms.commands.config import _flatten, _configCheck, _loadUserConfig, _writeConfig, config_init, config_exists, config_list, config_verify, config_reset

# -- Define tests for default config file structure
class TestLoadDefaultConfig:
    def test_returns_dict(self):
        cfg = loadDefaultConfig()
        assert isinstance(cfg, dict)

    def test_contains_expected_top_level_sections(self):
        cfg = loadDefaultConfig()
        for section in ('global', 'convert', 'search', 'percolator', 'quantify'):
            assert section in cfg, f'Missing top-level section: {section}'

    def test_search_section_has_required_keys(self):
        search = loadDefaultConfig()['search']
        for key in ('threads', 'precursor_tolerance_ppm', 'fragment_tolerance_da',
                    'missed_cleavages', 'score_function'):
            assert key in search, f'Missing search key: {key}'

    def test_values_have_correct_types(self):
        cfg = loadDefaultConfig()
        assert isinstance(cfg['search']['threads'], int)
        assert isinstance(cfg['search']['precursor_tolerance_ppm'], float)
        assert isinstance(cfg['convert']['gzip'], bool)

# -- Define tests for _flatten utility function
class TestFlatten:
    def test_flat_dict_unchanged(self):
        d = {'a': 1, 'b': 2}
        assert _flatten(d) == {'a': 1, 'b': 2}

    def test_nested_dict_flattened(self):
        d = {'outer': {'inner': 42}}
        assert _flatten(d) == {'outer.inner': 42}

    def test_deeply_nested(self):
        d = {'a': {'b': {'c': 'x'}}}
        assert _flatten(d) == {'a.b.c': 'x'}

    def test_mixed_depth(self):
        d = {'top': 1, 'nested': {'key': 2}}
        result = _flatten(d)
        assert result['top'] == 1
        assert result['nested.key'] == 2

    def test_empty_dict(self):
        assert _flatten({}) == {}

    def test_default_config_flattens_without_error(self):
        cfg = loadDefaultConfig()
        flat = _flatten(cfg)
        assert all('.' in k for k in flat if any(
            cfg.get(k.split('.')[0], None) and isinstance(cfg[k.split('.')[0]], dict)
            for _ in [None]
        ))
        assert isinstance(flat, dict)
        assert len(flat) > 0

# -- Define tests for checking configuration file exists
class TestConfigCheck:
    def test_exists_true_when_file_present(self, tmp_path):
        p = tmp_path / 'config.toml'
        p.write_text('[global]\nverbose = false\n')
        assert _configCheck(p, exists=True) is True

    def test_exists_true_fails_when_file_absent(self, tmp_path, capsys):
        p = tmp_path / 'config.toml'
        result = _configCheck(p, exists=True)
        assert result is False

    def test_exists_false_passes_when_file_absent(self, tmp_path):
        p = tmp_path / 'config.toml'
        assert _configCheck(p, exists=False) is True

    def test_exists_false_fails_when_file_present(self, tmp_path):
        p = tmp_path / 'config.toml'
        p.write_text('[global]\nverbose = false\n')
        assert _configCheck(p, exists=False) is False

# -- Define tests for writing and loading configuration files
class TestWriteLoadConfig:
    def test_write_and_reload_preserves_content(self, isolated_config_dir):
        defaults = loadDefaultConfig()
        _writeConfig(defaults)
        loaded = _loadUserConfig()
        assert loaded == defaults

    def test_load_raises_when_no_config(self, isolated_config_dir):
        with pytest.raises(FileNotFoundError):
            _loadUserConfig()

# -- Define tests for config init subcommand
class TestConfigInit:
    def test_creates_config_file(self, isolated_config_dir):
        from comms.utils.settings import userConfigPath
        config_init()
        assert userConfigPath().exists()

    def test_created_file_is_valid_toml(self, isolated_config_dir):
        from comms.utils.settings import userConfigPath
        config_init()
        with userConfigPath().open('rb') as f:
            result = tomllib.load(f)
        assert isinstance(result, dict)

    def test_does_not_overwrite_existing(self, isolated_config_dir):
        from comms.utils.settings import userConfigPath
        config_init()
        userConfigPath().write_text('[global]\nverbose = true\n')
        with pytest.raises(click.exceptions.Exit) as exc:
            config_init()
        assert exc.value.exit_code != 0

# -- Define tests for config exists subcommand
class TestConfigExists:
    def test_exits_nonzero_when_absent(self, isolated_config_dir):
        with pytest.raises(click.exceptions.Exit) as exc:
            config_exists()
        assert exc.value.exit_code != 0

    def test_does_not_raise_when_present(self, isolated_config_dir):
        config_init()
        config_exists()

# -- Define tests for config verify subcommand
class TestConfigVerify:
    def test_valid_config_passes(self, isolated_config_dir):
        config_init()
        config_verify()

    def test_missing_key_exits_nonzero(self, isolated_config_dir):
        from comms.utils.settings import userConfigPath
        config_init()
        # Remove one required key by writing a truncated config
        userConfigPath().write_text('[global]\nverbose = false\n')
        with pytest.raises(click.exceptions.Exit) as exc:
            config_verify()
        assert exc.value.exit_code != 0

    def test_exits_nonzero_when_no_config(self, isolated_config_dir):
        with pytest.raises(click.exceptions.Exit) as exc:
            config_verify()
        assert exc.value.exit_code != 0


# -- Define tests for config reset subcommand
class TestConfigReset:
    def test_reset_with_force_restores_defaults(self, isolated_config_dir):
        from comms.utils.settings import userConfigPath
        config_init()
        # Corrupt the config
        userConfigPath().write_text('[global]\nverbose = true\n')
        config_reset(force=True)
        loaded = _loadUserConfig()
        defaults = loadDefaultConfig()
        assert loaded == defaults

    def test_reset_without_force_prompts(self, isolated_config_dir, monkeypatch):
        config_init()
        # Simulate user declining the prompt
        monkeypatch.setattr('typer.confirm', lambda *a, **kw: False)
        with pytest.raises(click.exceptions.Exit) as exc:
            config_reset(force=False)
        assert exc.value.exit_code == 0
