'''
Unit tests for src/comms/commands/config.py and src/comms/utils/settings.py
'''

# -- Import external dependencies
import click, pytest, tomllib
from pathlib import Path

# -- Import internal functions
from comms.utils.settings import loadDefaultConfig, userConfigPath
from comms.commands.config import CARBAMIDOMETHYL_MOD, _apply_protocol_flags, _flatten, _configCheck, _loadUserConfig, _writeConfig, config_init, config_exists, config_list, config_verify, config_reset, config_set

# -- Define fixture for initialised user config file
@pytest.fixture()
def initialised_config(isolated_config_dir):
    '''
    Builds on isolated_config_dir: also calls config_init() so a valid user
    config file exists before the test runs.
    '''
    config_init()
    return isolated_config_dir

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

    def test_default_mods_spec_does_not_contain_carbamidomethyl(self):
        '''Check carbamidomethylation is not in default config'''
        mods = loadDefaultConfig()['search']['mods_spec']
        assert CARBAMIDOMETHYL_MOD not in mods

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

    def test_exists_true_fails_when_file_absent(self, tmp_path):
        p = tmp_path / 'config.toml'
        assert _configCheck(p, exists=True) is False

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
        config_init()
        assert userConfigPath().exists()

    def test_created_file_is_valid_toml(self, initialised_config):
        with userConfigPath().open('rb') as f:
            result = tomllib.load(f)
        assert isinstance(result, dict)

    def test_does_not_overwrite_existing(self, initialised_config):
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

    def test_does_not_raise_when_present(self, initialised_config):
        config_exists()

# -- Define tests for config verify subcommand
class TestConfigVerify:
    def test_valid_config_passes(self, initialised_config):
        config_verify()

    def test_missing_key_exits_nonzero(self, initialised_config):
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
    def test_reset_with_force_restores_defaults(self, initialised_config):
        # Corrupt the config
        userConfigPath().write_text('[global]\nverbose = true\n')
        config_reset(force=True)
        assert _loadUserConfig() == loadDefaultConfig()

    def test_reset_without_force_prompts(self, initialised_config, monkeypatch):
        # Simulate user declining the prompt
        monkeypatch.setattr('click.confirm', lambda *a, **kw: False)
        with pytest.raises(click.exceptions.Exit) as exc:
            config_reset(force=False)
        assert exc.value.exit_code in (0, None)

    def test_reset_without_force_proceeds_on_confirm(self, initialised_config, monkeypatch):
        userConfigPath().write_text('[global]\nverbose = true\n')
        monkeypatch.setattr('click.confirm', lambda *a, **kw: True)
        config_reset(force=False)
        assert _loadUserConfig() == loadDefaultConfig()

# Define tests for _apply_protocol_flags helper function
class TestApplyProtocolFlags:
    def test_iodo_adds_carbamidomethyl_to_empty_spec(self):
        result = _apply_protocol_flags('', iodo=True)
        assert f'1{CARBAMIDOMETHYL_MOD}' in result

    def test_iodo_adds_carbamidomethyl_to_existing_spec(self):
        result = _apply_protocol_flags('1M+15.9949', iodo=True)
        assert f'1{CARBAMIDOMETHYL_MOD}' in result
        assert '1M+15.9949' in result

    def test_iodo_prepends_carbamidomethyl(self):
        result = _apply_protocol_flags('1M+15.9949', iodo=True)
        assert result.startswith(f'1{CARBAMIDOMETHYL_MOD}')

    def test_no_iodo_removes_carbamidomethyl(self):
        spec = f'1{CARBAMIDOMETHYL_MOD},1M+15.9949'
        result = _apply_protocol_flags(spec, iodo=False)
        assert CARBAMIDOMETHYL_MOD not in result
        assert '1M+15.9949' in result

    def test_no_iodo_on_spec_without_cys_is_noop(self):
        spec = '1M+15.9949'
        result = _apply_protocol_flags(spec, iodo=False)
        assert result == spec

    def test_iodo_replaces_existing_cys_mod(self):
        '''Any pre-existing Cys mod should be replaced, not duplicated.'''
        spec = f'1{CARBAMIDOMETHYL_MOD},1M+15.9949'
        result = _apply_protocol_flags(spec, iodo=True)
        assert result.count('C+') == 1

    def test_iodo_replaces_alternative_cys_mod(self):
        '''A different Cys mod (e.g. propionamide) should be replaced by carbamidomethyl.'''
        spec = '1C+71.0371,1M+15.9949'   # propionamide on Cys
        result = _apply_protocol_flags(spec, iodo=True)
        assert f'1{CARBAMIDOMETHYL_MOD}' in result
        assert '1C+71.0371' not in result

    def test_no_iodo_removes_alternative_cys_mod(self):
        '''--no-iodo should remove any Cys mod, not just carbamidomethyl.'''
        spec = '1C+71.0371,1M+15.9949'
        result = _apply_protocol_flags(spec, iodo=False)
        assert 'C+' not in result
        assert '1M+15.9949' in result

    def test_empty_spec_no_iodo_returns_empty(self):
        result = _apply_protocol_flags('', iodo=False)
        assert result == ''

    def test_result_has_no_leading_or_trailing_commas(self):
        result = _apply_protocol_flags('', iodo=True)
        assert not result.startswith(',')
        assert not result.endswith(',')

    def test_result_has_no_double_commas(self):
        result = _apply_protocol_flags('1M+15.9949', iodo=True)
        assert ',,' not in result

# Define tests for config set subcommand
class TestConfigSet:
    def test_creates_config_if_absent(self, isolated_config_dir):
        '''config_set should auto-create the user config if none exists.'''
        config_set(iodo=True)
        assert userConfigPath().exists()

    def test_created_config_is_valid_toml(self, isolated_config_dir):
        config_set(iodo=True)
        with userConfigPath().open('rb') as f:
            result = tomllib.load(f)
        assert isinstance(result, dict)

    def test_iodo_adds_mod_to_mods_spec(self, initialised_config):
        config_set(iodo=True)
        cfg = _loadUserConfig()
        assert CARBAMIDOMETHYL_MOD in cfg['search']['mods_spec']

    def test_no_iodo_removes_mod_from_mods_spec(self, initialised_config):
        config_set(iodo=True)
        config_set(iodo=False)
        cfg = _loadUserConfig()
        assert CARBAMIDOMETHYL_MOD not in cfg['search']['mods_spec']

    def test_iodo_is_idempotent(self, initialised_config):
        '''Calling config_set(iodo=True) twice should not duplicate the mod.'''
        config_set(iodo=True)
        config_set(iodo=True)
        cfg = _loadUserConfig()
        assert cfg['search']['mods_spec'].count('C+') == 1

    def test_no_iodo_is_idempotent(self, initialised_config):
        config_set(iodo=False)
        config_set(iodo=False)
        cfg = _loadUserConfig()
        assert CARBAMIDOMETHYL_MOD not in cfg['search']['mods_spec']

    def test_other_mods_preserved_after_iodo(self, initialised_config):
        '''Setting --iodo should not affect non-Cys mods.'''
        original_mods = _loadUserConfig()['search']['mods_spec']
        config_set(iodo=True)
        updated_mods = _loadUserConfig()['search']['mods_spec']
        remaining = ','.join(
            e for e in updated_mods.split(',')
            if CARBAMIDOMETHYL_MOD not in e
        )
        assert remaining == original_mods

    def test_other_mods_preserved_after_no_iodo(self, initialised_config):
        config_set(iodo=True)
        original_non_cys = ','.join(
            e for e in _loadUserConfig()['search']['mods_spec'].split(',')
            if CARBAMIDOMETHYL_MOD not in e
        )
        config_set(iodo=False)
        assert _loadUserConfig()['search']['mods_spec'] == original_non_cys

    def test_no_flag_exits_nonzero(self, isolated_config_dir):
        with pytest.raises(click.exceptions.Exit) as exc:
            config_set(iodo=None)
        assert exc.value.code != 0

    def test_all_other_config_keys_unchanged_after_set(self, initialised_config):
        '''config_set should only touch search.mods_spec.'''
        before = _loadUserConfig()
        config_set(iodo=True)
        after = _loadUserConfig()
        for section, values in before.items():
            if section == 'search':
                for key, val in values.items():
                    if key != 'mods_spec':
                        assert after[section][key] == val, (
                            f'config_set unexpectedly changed {section}.{key}'
                        )
            else:
                assert after[section] == values, (
                    f'config_set unexpectedly changed section [{section}]'
                )