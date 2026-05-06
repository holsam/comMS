'''
Unit tests for src/comms/commands/config.py and src/comms/utils/settings.py
'''

# -- Import external dependencies
import click, pytest, tomllib
from pathlib import Path

# -- Import internal functions
import comms.utils.settings as settings
from comms.commands.config import CARBAMIDOMETHYL_MOD, MZ_BIN_WIDTH_HIGH_RES, MZ_BIN_WIDTH_LOW_RES, SCORE_FUNC_HIGH_RES, SCORE_FUNC_LOW_RES, _apply_organism, _apply_protocol_flags, _apply_iodo, _flatten, _configCheck, _loadUserConfig, _parse_organism_arg, _writeConfig, config_init, config_exists, config_list, config_verify, config_reset, config_set

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
        cfg = settings.loadDefaultConfig()
        assert isinstance(cfg, dict)

    def test_contains_expected_top_level_sections(self):
        cfg = settings.loadDefaultConfig()
        for section in ('global', 'convert', 'search', 'percolator', 'quantify'):
            assert section in cfg, f'Missing top-level section: {section}'

    def test_search_section_has_required_keys(self):
        search = settings.loadDefaultConfig()['search']
        for key in ('threads', 'precursor_tolerance_ppm', 'mz_bin_width', 'missed_cleavages', 'score_function'):
            assert key in search, f'Missing search key: {key}'

    def test_no_fragment_tolerance_da_key(self):
        '''fragment_tolerance_da has been replaced by mz_bin_width.'''
        assert 'fragment_tolerance_da' not in settings.loadDefaultConfig().get('search', {})

    def test_values_have_correct_types(self):
        cfg = settings.loadDefaultConfig()
        assert isinstance(cfg['search']['threads'], int)
        assert isinstance(cfg['search']['precursor_tolerance_ppm'], float)
        assert isinstance(cfg['search']['mz_bin_width'], float)
        assert isinstance(cfg['convert']['gzip'], bool)

    def test_default_score_function_is_xcorr(self):
        assert settings.loadDefaultConfig()['search']['score_function'] == SCORE_FUNC_HIGH_RES

    def test_default_mz_bin_width_is_high_res(self):
        assert settings.loadDefaultConfig()['search']['mz_bin_width'] == MZ_BIN_WIDTH_HIGH_RES

    def test_default_mods_spec_does_not_contain_carbamidomethyl(self):
        '''Check carbamidomethylation is not in default config'''
        mods = settings.loadDefaultConfig()['search']['mods_spec']
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
        cfg = settings.loadDefaultConfig()
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
        defaults = settings.loadDefaultConfig()
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
        assert settings.userConfigPath().exists()

    def test_created_file_is_valid_toml(self, isolated_config_dir):
        config_init()
        with settings.userConfigPath().open('rb') as f:
            result = tomllib.load(f)
        assert isinstance(result, dict)

    def test_does_not_overwrite_existing(self, initialised_config):
        settings.userConfigPath().write_text('[global]\nverbose = true\n')
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
        settings.userConfigPath().write_text('[global]\nverbose = false\n')
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
        settings.userConfigPath().write_text('[global]\nverbose = true\n')
        config_reset(force=True)
        assert _loadUserConfig() == settings.loadDefaultConfig()

    def test_reset_without_force_prompts(self, initialised_config, monkeypatch):
        # Simulate user declining the prompt
        monkeypatch.setattr('typer.confirm', lambda *a, **kw: False)
        with pytest.raises(click.exceptions.Exit) as exc:
            config_reset(force=False)
        assert exc.value.exit_code in (0, None)

    def test_reset_without_force_proceeds_on_confirm(self, isolated_config_dir, monkeypatch):
        settings.userConfigPath().write_text('[global]\nverbose = true\n')
        monkeypatch.setattr('typer.confirm', lambda *a, **kw: True)
        config_reset(force=False)
        assert _loadUserConfig() == settings.loadDefaultConfig()

# -- Define tests for _apply_organism helper function
class TestApplyOrganism:
    def test_sets_organism_section(self):
        cfg = {'organism': {}, 'search': {'threads': 2}}
        result = _apply_organism(cfg, {'Test1': 'TEST1', 'Test2': 'TEST2'})
        assert result['organism'] == {'Test1': 'TEST1', 'Test2': 'TEST2'}
    
    def test_replaces_existing_organism_section(self):
        cfg = {'organism': {'OldTest', 'OLDTEST'}}
        result = _apply_organism(cfg, {'NewTest': 'NEWTEST'})
        assert 'OldTest' not in result['organism']
        assert result['organism'] == {'NewTest': 'NEWTEST'}
    
    def test_does_not_touch_other_sections(self):
        cfg = {'organism': {}, 'search': {'threads': 2}, 'percolator': {'psm_fdr': 0.01}}
        _apply_organism(cfg, {'Test': 'TEST'})
        assert cfg['search']['threads'] == 2
        assert cfg['percolator']['psm_fdr'] == 0.01
    
    def test_empty_dict_clears_organism_section(self):
        cfg = {'organism': {'Test', 'TEST'}}
        result = _apply_organism(cfg, {})
        assert result['organism'] == {}
    
    def test_returns_cfg(self):
        cfg = {'organism': {}}
        result = _apply_organism(cfg, {'Test': 'TEST'})
        assert result is cfg

# -- Define tests for _apply_iodo helper function
class TestApplyIodo:
    def test_iodo_adds_carbamidomethyl_to_empty_spec(self):
        result = _apply_iodo('', iodo=True)
        assert f'1{CARBAMIDOMETHYL_MOD}' in result

    def test_iodo_adds_carbamidomethyl_to_existing_spec(self):
        result = _apply_iodo('1M+15.9949', iodo=True)
        assert f'1{CARBAMIDOMETHYL_MOD}' in result
        assert '1M+15.9949' in result

    def test_iodo_prepends_carbamidomethyl(self):
        result = _apply_iodo('1M+15.9949', iodo=True)
        assert result.startswith(f'1{CARBAMIDOMETHYL_MOD}')

    def test_no_iodo_removes_carbamidomethyl(self):
        spec = f'1{CARBAMIDOMETHYL_MOD},1M+15.9949'
        result = _apply_iodo(spec, iodo=False)
        assert CARBAMIDOMETHYL_MOD not in result
        assert '1M+15.9949' in result

    def test_no_iodo_on_spec_without_cys_is_noop(self):
        spec = '1M+15.9949'
        result = _apply_iodo(spec, iodo=False)
        assert result == spec

    def test_iodo_replaces_existing_cys_mod(self):
        '''Any pre-existing Cys mod should be replaced, not duplicated.'''
        spec = f'1{CARBAMIDOMETHYL_MOD},1M+15.9949'
        result = _apply_iodo(spec, iodo=True)
        assert result.count('C+') == 1

    def test_iodo_replaces_alternative_cys_mod(self):
        '''A different Cys mod (e.g. propionamide) should be replaced by carbamidomethyl.'''
        spec = '1C+71.0371,1M+15.9949'   # propionamide on Cys
        result = _apply_iodo(spec, iodo=True)
        assert f'1{CARBAMIDOMETHYL_MOD}' in result
        assert '1C+71.0371' not in result

    def test_no_iodo_removes_alternative_cys_mod(self):
        '''--no-iodo should remove any Cys mod, not just carbamidomethyl.'''
        spec = '1C+71.0371,1M+15.9949'
        result = _apply_iodo(spec, iodo=False)
        assert 'C+' not in result
        assert '1M+15.9949' in result

    def test_empty_spec_no_iodo_returns_empty(self):
        result = _apply_iodo('', iodo=False)
        assert result == ''

    def test_result_has_no_leading_or_trailing_commas(self):
        result = _apply_iodo('', iodo=True)
        assert not result.startswith(',')
        assert not result.endswith(',')

    def test_result_has_no_double_commas(self):
        result = _apply_iodo('1M+15.9949', iodo=True)
        assert ',,' not in result

# -- Define tests for _apply_protocol_flags helper function
class TestApplyProtocolFlags:
    def _base_cfg(self):
        return settings.loadDefaultConfig()

    def test_iodo_none_does_not_touch_mods_spec(self):
        cfg = self._base_cfg()
        original = cfg['search']['mods_spec']
        result = _apply_protocol_flags(cfg, iodo=None, low_res=None)
        assert result['search']['mods_spec'] == original

    def test_low_res_none_does_not_touch_search(self):
        cfg = self._base_cfg()
        original_bw = cfg['search']['mz_bin_width']
        original_sf = cfg['search']['score_function']
        result = _apply_protocol_flags(cfg, iodo=None, low_res=None)
        assert result['search']['mz_bin_width'] == original_bw
        assert result['search']['score_function'] == original_sf

    def test_low_res_true_sets_bin_width_and_score(self):
        cfg = _apply_protocol_flags(self._base_cfg(), iodo=None, low_res=True)
        assert cfg['search']['mz_bin_width'] == MZ_BIN_WIDTH_LOW_RES
        assert cfg['search']['score_function'] == SCORE_FUNC_LOW_RES

    def test_low_res_false_sets_high_res_bin_width_and_score(self):
        cfg = _apply_protocol_flags(self._base_cfg(), iodo=None, low_res=False)
        assert cfg['search']['mz_bin_width'] == MZ_BIN_WIDTH_HIGH_RES
        assert cfg['search']['score_function'] == SCORE_FUNC_HIGH_RES

    def test_combined_iodo_and_low_res(self):
        cfg = _apply_protocol_flags(self._base_cfg(), iodo=True, low_res=True)
        assert CARBAMIDOMETHYL_MOD in cfg['search']['mods_spec']
        assert cfg['search']['mz_bin_width'] == MZ_BIN_WIDTH_LOW_RES
        assert cfg['search']['score_function'] == SCORE_FUNC_LOW_RES

    def test_combined_iodo_and_high_res(self):
        cfg = _apply_protocol_flags(self._base_cfg(), iodo=True, low_res=False)
        assert CARBAMIDOMETHYL_MOD in cfg['search']['mods_spec']
        assert cfg['search']['mz_bin_width'] == MZ_BIN_WIDTH_HIGH_RES
        assert cfg['search']['score_function'] == SCORE_FUNC_HIGH_RES

    def test_only_relevant_keys_touched_by_low_res(self):
        cfg_before = self._base_cfg()
        cfg_after  = _apply_protocol_flags(self._base_cfg(), iodo=None, low_res=True)
        for key in ('threads', 'precursor_tolerance_ppm', 'mods_spec', 'missed_cleavages', 'min_peaks'):
            assert cfg_after['search'][key] == cfg_before['search'][key], (f'_apply_protocol_flags unexpectedly changed search.{key}')

    def test_non_search_sections_untouched(self):
        cfg_before = self._base_cfg()
        cfg_after  = _apply_protocol_flags(self._base_cfg(), iodo=True, low_res=True)
        for section in ('global', 'convert', 'percolator', 'quantify'):
            assert cfg_after.get(section) == cfg_before.get(section), (f'_apply_protocol_flags unexpectedly changed section [{section}]')

# -- Define tests for _parse_organism_arg helper function
class TestParseOrganismArg:
    def test_parses_single_pair(self):
        result = _parse_organism_arg(['TestOrg=TEST'])
        assert result == {'TestOrg': 'TEST'}

    def test_parses_multiple_pairs(self):
        result = _parse_organism_arg(['TestOrg1=TEST1', 'TestOrg2=TEST2'])
        assert result == {'TestOrg1': 'TEST1', 'TestOrg2': 'TEST2'}

    def test_strips_whitespace_from_key_and_pattern(self):
        result = _parse_organism_arg(['Test = TEST'])
        assert result == {'Test': 'TEST'}

    def test_preserves_regex_characters_in_pattern(self):
        result = _parse_organism_arg(['Test=TEST$'])
        assert result['Test'] == 'TEST$'
    
    def test_raises_system_exit_when_no_equals_sign(self):
        with pytest.raises(SystemExit):
            _parse_organism_arg(['TestTEST'])

    def test_raises_system_exit_when_key_is_empty(self):
        with pytest.raises(SystemExit):
            _parse_organism_arg(['=TEST'])

    def test_raises_system_exit_when_pattern_is_empty(self):
        with pytest.raises(SystemExit):
            _parse_organism_arg(['Test='])

    def test_returns_dict(self):
        assert isinstance(_parse_organism_arg(['Test=TEST']), dict)

    def test_empty_list_returns_empty_dict(self):
        result = _parse_organism_arg([])
        assert result == {}

    def test_pattern_containing_equals_sign_is_preserved(self):
        result = _parse_organism_arg(['Test=TE=ST'])
        assert result == {'Test': 'TE=ST'}

# Define tests for config set subcommand
class TestConfigSet:
    def test_creates_config_if_absent(self, isolated_config_dir):
        '''config_set should auto-create the user config if none exists'''
        config_set(iodo=True, low_res=None, organism=None)
        assert settings.userConfigPath().exists()

    def test_created_config_is_valid_toml(self, isolated_config_dir):
        config_set(iodo=True, low_res=None, organism=None)
        with settings.userConfigPath().open('rb') as f:
            result = tomllib.load(f)
        assert isinstance(result, dict)

    def test_iodo_adds_mod_to_mods_spec(self, initialised_config):
        config_set(iodo=True, low_res=None)
        cfg = _loadUserConfig()
        assert CARBAMIDOMETHYL_MOD in cfg['search']['mods_spec']

    def test_no_iodo_removes_mod_from_mods_spec(self, initialised_config):
        config_set(iodo=True,  low_res=None)
        config_set(iodo=False, low_res=None)
        cfg = _loadUserConfig()
        assert CARBAMIDOMETHYL_MOD not in cfg['search']['mods_spec']

    def test_iodo_is_idempotent(self, initialised_config):
        '''Calling config_set(iodo=True) twice should not duplicate the mod'''
        config_set(iodo=True, low_res=None)
        config_set(iodo=True, low_res=None)
        cfg = _loadUserConfig()
        assert cfg['search']['mods_spec'].count('C+') == 1

    def test_no_iodo_is_idempotent(self, initialised_config):
        config_set(iodo=False, low_res=None)
        config_set(iodo=False, low_res=None)
        cfg = _loadUserConfig()
        assert CARBAMIDOMETHYL_MOD not in cfg['search']['mods_spec']

    def test_other_mods_preserved_after_iodo(self, initialised_config):
        '''Setting --iodo should not affect non-Cys mods'''
        original_mods = _loadUserConfig()['search']['mods_spec']
        config_set(iodo=True, low_res=None)
        updated_mods = _loadUserConfig()['search']['mods_spec']
        remaining = ','.join(e for e in updated_mods.split(',') if CARBAMIDOMETHYL_MOD not in e)
        assert remaining == original_mods

    def test_other_mods_preserved_after_no_iodo(self, initialised_config):
        config_set(iodo=True, low_res=None)
        original_non_cys = ','.join(e for e in _loadUserConfig()['search']['mods_spec'].split(',') if CARBAMIDOMETHYL_MOD not in e)
        config_set(iodo=False)
        assert _loadUserConfig()['search']['mods_spec'] == original_non_cys

    def test_low_res_sets_bin_width_and_score(self, initialised_config):
        config_set(iodo=None, low_res=True)
        cfg = _loadUserConfig()
        assert cfg['search']['mz_bin_width']   == MZ_BIN_WIDTH_LOW_RES
        assert cfg['search']['score_function'] == SCORE_FUNC_LOW_RES

    def test_high_res_sets_bin_width_and_score(self, initialised_config):
        config_set(iodo=None, low_res=False)
        cfg = _loadUserConfig()
        assert cfg['search']['mz_bin_width']   == MZ_BIN_WIDTH_HIGH_RES
        assert cfg['search']['score_function'] == SCORE_FUNC_HIGH_RES

    def test_low_res_is_idempotent(self, initialised_config):
        config_set(iodo=None, low_res=True)
        config_set(iodo=None, low_res=True)
        cfg = _loadUserConfig()
        assert cfg['search']['mz_bin_width']   == MZ_BIN_WIDTH_LOW_RES
        assert cfg['search']['score_function'] == SCORE_FUNC_LOW_RES

    def test_sets_organism_in_config(self, initialised_config):
        config_set(iodo=None, low_res=None, organism=['Test1=TEST1', 'Test2=TEST2'])
        cfg = _loadUserConfig()
        assert cfg['organism'] == {'Test1': 'TEST1', 'Test2': 'TEST2'}
    
    def test_set_organism_replaces_existing(self, initialised_config):
        config_set(iodo=None, low_res=None, organism=['Test1=TEST1', 'Test2=TEST2'])
        config_set(iodo=None, low_res=None, organism=['Test1=NEWTEST1'])
        cfg = _loadUserConfig()
        assert cfg['organism'] == {'Test1': 'NEWTEST1'}
        assert 'Test2' not in cfg['organism']

    def test_organism_section_written_as_toml_table(self, initialised_config):
        config_set(iodo=None, low_res=None, organism=['Test1=TEST1', 'Test2=TEST2'])
        cfg = _loadUserConfig()
        assert isinstance(cfg['organism'], dict)
        assert isinstance(cfg['organism']['Test1'], str)

    def test_combined_iodo_and_low_res(self, initialised_config):
        config_set(iodo=True, low_res=True)
        cfg = _loadUserConfig()
        assert CARBAMIDOMETHYL_MOD in cfg['search']['mods_spec']
        assert cfg['search']['mz_bin_width']   == MZ_BIN_WIDTH_LOW_RES
        assert cfg['search']['score_function'] == SCORE_FUNC_LOW_RES

    def test_combined_iodo_and_high_res(self, initialised_config):
        config_set(iodo=True, low_res=False)
        cfg = _loadUserConfig()
        assert CARBAMIDOMETHYL_MOD in cfg['search']['mods_spec']
        assert cfg['search']['mz_bin_width'] == MZ_BIN_WIDTH_HIGH_RES
        assert cfg['search']['score_function'] == SCORE_FUNC_HIGH_RES

    def test_combined_organism_and_iodo(self, initialised_config):
        config_set(iodo=True, low_res=None, organism=['Test1=TEST1', 'Test2=TEST2'])
        cfg = _loadUserConfig()
        assert cfg['organism'] == {'Test1': 'TEST1', 'Test2': 'TEST2'}
        assert CARBAMIDOMETHYL_MOD in cfg['search']['mods_spec']

    def test_combined_organism_and_low_res(self, initialised_config):
        config_set(iodo=None, low_res=True, organism=['Test1=TEST1'])
        cfg = _loadUserConfig()
        assert cfg['organism'] == {'Test1': 'TEST1'}
        assert cfg['search']['mz_bin_width'] == MZ_BIN_WIDTH_LOW_RES

    def test_combined_organism_and_iodo(self, initialised_config):
        config_set(iodo=True, low_res=None, organism=['Test1=TEST1', 'Test2=TEST2'])
        cfg = _loadUserConfig()
        assert cfg['organism'] == {'Test1': 'TEST1', 'Test2': 'TEST2'}
        assert CARBAMIDOMETHYL_MOD in cfg['search']['mods_spec']

    def test_combined_organism_and_high_res(self, initialised_config):
        config_set(iodo=None, low_res=False, organism=['Test1=TEST1'])
        cfg = _loadUserConfig()
        assert cfg['organism'] == {'Test1': 'TEST1'}
        assert cfg['search']['mz_bin_width'] == MZ_BIN_WIDTH_HIGH_RES

    def test_no_flags_exits_nonzero(self, isolated_config_dir):
        with pytest.raises((SystemExit, click.exceptions.Exit)) as exc:
            config_set(iodo=None, low_res=None, organism=None)
        assert exc.value.exit_code != 0

    def test_all_other_config_keys_unchanged_after_set(self, initialised_config):
        before = _loadUserConfig()
        config_set(iodo=True, low_res=True)
        after = _loadUserConfig()
        for section, values in before.items():
            if section == 'search':
                for key, val in values.items():
                    if key not in ('mods_spec', 'mz_bin_width', 'score_function'):
                        assert after[section][key] == val, (
                            f'config_set unexpectedly changed {section}.{key}'
                        )
            else:
                assert after[section] == values, (
                    f'config_set unexpectedly changed section [{section}]'
                )

    def test_other_sections_unchanged_after_organism_set(self, initialised_config):
        before = _loadUserConfig()
        config_set(iodo=None, low_res=None, organism=['Mt=MEDTR'])
        after = _loadUserConfig()
        for section in ('search', 'percolator', 'quantify', 'convert', 'global'):
            assert after.get(section) == before.get(section), (
                f'config_set --organism unexpectedly changed section [{section}]'
            )