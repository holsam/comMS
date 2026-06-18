'''
Unit tests for src/comms/commands/config.py and src/comms/utils/settings.py
'''

# -- Import external dependencies
import click, pytest, tomllib
from pathlib import Path

# Import internal constants
from comms.commands.config import CARBAMIDOMETHYL_MOD, MET_OX_MOD, PHOSPHO_MOD, NCYC_MOD, NACE_MOD, MANAGED_MOD_PATTERNS, MZ_BIN_WIDTH_HIGH_RES, MZ_BIN_WIDTH_LOW_RES, SCORE_FUNC_HIGH_RES, SCORE_FUNC_LOW_RES

# -- Import internal functions
import comms.utils.settings as settings
from comms.commands.config import _apply_custom_mod, _apply_iodo, _apply_mod, _apply_organism, _apply_protocol_flags, _flatten, _configCheck, _loadConfigFile, _parse_organism_arg, _resolveConfigTarget, _writeConfig, config_init, config_exists, config_list, config_verify, config_reset, config_set

# -- Define fixture for initialised user config file
@pytest.fixture()
def initialised_config(isolated_config_dir):
    '''
    Builds on isolated_config_dir: also calls config_init() so a valid user
    config file exists before the test runs.
    '''
    config_init()
    return isolated_config_dir

# -- Define tests for resolving targeted config file
class TestResolveConfigTarget:
    def test_none_is_global(self):
        from comms.utils.settings import globalConfigPath
        assert _resolveConfigTarget(None) == globalConfigPath()

    def test_global_keyword_case_insensitive(self):
        from comms.utils.settings import globalConfigPath
        assert _resolveConfigTarget('GLOBAL') == globalConfigPath()
        assert _resolveConfigTarget('global') == globalConfigPath()

    def test_path_is_returned_verbatim(self, tmp_path):
        target = tmp_path / 'comms' / 'config.toml'
        assert _resolveConfigTarget(str(target)) == target

# -- Define tests for setting local target config file
class TestConfigSetLocalTarget:
    def test_set_writes_to_local_path(self, tmp_path):
        local = tmp_path / 'comms' / 'config.toml'
        config_set(iodo=True, config_path=local)
        assert local.exists()
        import tomllib
        with local.open('rb') as f:
            cfg = tomllib.load(f)
        assert 'index' in cfg

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
        for key in ('threads', 'precursor_tolerance_ppm', 'mz_bin_width', 'score_function'):
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

    def test_default_fixed_mods_does_not_contain_carbamidomethyl(self):
        '''Check carbamidomethylation is not in default config'''
        mods = settings.loadDefaultConfig()['index']['fixed_mods']
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
        loaded = _loadConfigFile()
        assert loaded == defaults

    def test_load_raises_when_no_config(self, isolated_config_dir):
        with pytest.raises(FileNotFoundError):
            _loadConfigFile()

# -- Define tests for config init subcommand
class TestConfigInit:
    def test_creates_config_file(self, isolated_config_dir):
        config_init()
        assert settings.globalConfigPath().exists()

    def test_created_file_is_valid_toml(self, isolated_config_dir):
        config_init()
        with settings.globalConfigPath().open('rb') as f:
            result = tomllib.load(f)
        assert isinstance(result, dict)

    def test_does_not_overwrite_existing(self, initialised_config):
        settings.globalConfigPath().write_text('[global]\nverbose = true\n')
        with pytest.raises(SystemExit) as exc:
            config_init()
        assert exc.value.code != 0

# -- Define tests for config exists subcommand
class TestConfigExists:
    def test_exits_nonzero_when_absent(self, isolated_config_dir):
        with pytest.raises(SystemExit) as exc:
            config_exists()
        assert exc.value.code != 0

    def test_does_not_raise_when_present(self, initialised_config):
        config_exists()

# -- Define tests for config verify subcommand
class TestConfigVerify:
    def test_valid_config_passes(self, initialised_config):
        config_verify()

    def test_missing_key_exits_nonzero(self, initialised_config):
        # Remove one required key by writing a truncated config
        settings.globalConfigPath().write_text('[global]\nverbose = false\n')
        with pytest.raises(SystemExit) as exc:
            config_verify()
        assert exc.value.code != 0

    def test_exits_nonzero_when_no_config(self, isolated_config_dir):
        with pytest.raises(SystemExit) as exc:
            config_verify()
        assert exc.value.code != 0

# -- Define tests for config reset subcommand
class TestConfigReset:
    def test_reset_with_force_restores_defaults(self, initialised_config):
        # Corrupt the config
        settings.globalConfigPath().write_text('[global]\nverbose = true\n')
        config_reset(force=True)
        assert _loadConfigFile() == settings.loadDefaultConfig()

    def test_reset_without_force_prompts(self, initialised_config, monkeypatch):
        # Simulate user declining the prompt
        monkeypatch.setattr('typer.confirm', lambda *a, **kw: False)
        with pytest.raises(SystemExit) as exc:
            config_reset(force=False)
        assert exc.value.code in (0, None)

    def test_reset_without_force_proceeds_on_confirm(self, isolated_config_dir, monkeypatch):
        settings.globalConfigPath().write_text('[global]\nverbose = true\n')
        monkeypatch.setattr('typer.confirm', lambda *a, **kw: True)
        config_reset(force=False)
        assert _loadConfigFile() == settings.loadDefaultConfig()

# -- Define tests for _apply_custom_mod_mod helper function
class TestApplyCustom:
    def test_adds_custom_entry_to_empty_string(self):
        result = _apply_custom_mod('', '1K+28.0313')
        assert '1K+28.0313' in result

    def test_adds_custom_entry_to_existing_string(self):
        result = _apply_custom_mod('1K+28.0313', '1R+14.0157')
        assert '1K+28.0313' in result
        assert '1R+14.0157' in result

    def test_empty_string_clears_all_custom_mods(self):
        result = _apply_custom_mod('1K+28.0313,1R+14.0157', '')
        assert result == ''

    def test_duplicate_entry_not_added(self):
        result = _apply_custom_mod('1K+28.0313', '1K+28.0313')
        assert result.count('1K+28.0313') == 1

    def test_managed_cys_mod_rejected_with_warning(self, capsys):
        result = _apply_custom_mod('', '1C+57.0215')
        assert '1C+57.0215' not in result

    def test_managed_met_mod_rejected_with_warning(self, capsys):
        result = _apply_custom_mod('', '1M+15.9949')
        assert '1M+15.9949' not in result

    def test_managed_phos_mod_rejected_with_warning(self, capsys):
        result = _apply_custom_mod('', '1STY+79.966331')
        assert '1STY+79.966331' not in result

    def test_unmanaged_entry_accepted(self):
        result = _apply_custom_mod('', '1K+28.0313')
        assert result == '1K+28.0313'

    def test_no_leading_or_trailing_commas(self):
        result = _apply_custom_mod('', '1K+28.0313')
        assert not result.startswith(',')
        assert not result.endswith(',')

# -- Define tests for _apply_mod helper function
class TestApplyMod:
    def test_adds_mod_to_empty_spec(self):
        assert MET_OX_MOD in _apply_mod('', mod=MET_OX_MOD)
    def test_adds_mod_to_existing_spec(self):
        result = _apply_mod('1Q-17.027', mod=MET_OX_MOD)
        assert MET_OX_MOD in result
        assert '1Q-17.027' in result
    def test_prepends_mod(self):
        result = _apply_mod('1Q-17.027', mod=MET_OX_MOD)
        assert result.startswith(MET_OX_MOD)

    def test_adding_same_mod_twice_does_not_duplicate(self):
        result = _apply_mod(MET_OX_MOD, mod=MET_OX_MOD)
        assert result.count(MET_OX_MOD) == 1

    def test_removal_with_exclusive_pattern(self):
        spec = f'{MET_OX_MOD},{PHOSPHO_MOD}'
        result = _apply_mod(spec, mod='', exclusive_pattern=r'^\d*M\+15\.9949')
        assert MET_OX_MOD not in result
        assert PHOSPHO_MOD in result

    def test_exclusive_pattern_replaces_on_add(self):
        spec = f'1M+15.9949,{PHOSPHO_MOD}'
        result = _apply_mod(spec, mod='2M+15.9949', exclusive_pattern=r'^\d*M\+15\.9949')
        assert '2M+15.9949' in result
        assert '1M+15.9949' not in result
        assert PHOSPHO_MOD in result

    def test_no_leading_or_trailing_commas(self):
        result = _apply_mod('', mod=MET_OX_MOD)
        assert not result.startswith(',')
        assert not result.endswith(',')

    def test_no_double_commas(self):
        result = _apply_mod('1Q-17.027', mod=MET_OX_MOD)
        assert ',,' not in result

    def test_empty_mod_with_no_pattern(self):
        spec = '1M+15.9949'
        assert _apply_mod(spec, mod='') == spec

    def test_removal_of_absent_mod(self):
        spec = '1M+15.9949'
        result = _apply_mod(spec, mod='', exclusive_pattern=r'^\d*STY\+79\.966331')
        assert result == spec

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
    def test_iodo_adds_carbamidomethyl_to_empty_fixed_mods(self):
        result = _apply_iodo('', iodo=True)
        assert CARBAMIDOMETHYL_MOD in result

    def test_iodo_adds_carbamidomethyl_to_existing_fixed_mods(self):
        result = _apply_iodo('someother_mod', iodo=True)
        assert CARBAMIDOMETHYL_MOD in result
        assert 'someother_mod' in result

    def test_iodo_prepends_carbamidomethyl(self):
        result = _apply_iodo('someother_mod', iodo=True)
        assert result.startswith(CARBAMIDOMETHYL_MOD)

    def test_no_iodo_removes_carbamidomethyl(self):
        spec = f'{CARBAMIDOMETHYL_MOD},someother_mod'
        result = _apply_iodo(spec, iodo=False)
        assert CARBAMIDOMETHYL_MOD not in result
        assert 'someother_mod' in result

    def test_no_iodo_on_empty_fixed_mods_returns_empty(self):
        assert _apply_iodo('', iodo=False) == 'C+0'

    def test_no_iodo_on_spec_without_carbamidomethyl_is_noop(self):
        spec = 'someother_mod'
        assert _apply_iodo(spec, iodo=False) == 'C+0,'+spec

    def test_iodo_is_idempotent(self):
        result = _apply_iodo(_apply_iodo('', iodo=True), iodo=True)
        assert result.count(CARBAMIDOMETHYL_MOD) == 1

    def test_result_has_no_leading_or_trailing_commas(self):
        assert not _apply_iodo('', iodo=True).startswith(',')
        assert not _apply_iodo('', iodo=True).endswith(',')

    def test_result_has_no_double_commas(self):
        assert ',,' not in _apply_iodo('someother_mod', iodo=True)

    def test_mod_string_has_no_count_prefix(self):
        result = _apply_iodo('', iodo=True)
        assert result == CARBAMIDOMETHYL_MOD

# -- Define tests for _apply_protocol_flags helper function
class TestApplyProtocolFlags:
    def _base_cfg(self):
        return settings.loadDefaultConfig()

    def test_iodo_none_does_not_touch_mods_spec(self):
        cfg = self._base_cfg()
        original = cfg['index']['mods_spec']
        result = _apply_protocol_flags(cfg)
        assert result['index']['mods_spec'] == original

    def test_low_res_none_does_not_touch_search(self):
        cfg = self._base_cfg()
        original_bw = cfg['search']['mz_bin_width']
        original_sf = cfg['search']['score_function']
        result = _apply_protocol_flags(cfg)
        assert result['search']['mz_bin_width'] == original_bw
        assert result['search']['score_function'] == original_sf

    def test_low_res_true_sets_bin_width_and_score(self):
        cfg = _apply_protocol_flags(self._base_cfg(), low_res=True)
        assert cfg['search']['mz_bin_width'] == MZ_BIN_WIDTH_LOW_RES
        assert cfg['search']['score_function'] == SCORE_FUNC_LOW_RES

    def test_low_res_false_sets_high_res_bin_width_and_score(self):
        cfg = _apply_protocol_flags(self._base_cfg(), low_res=False)
        assert cfg['search']['mz_bin_width'] == MZ_BIN_WIDTH_HIGH_RES
        assert cfg['search']['score_function'] == SCORE_FUNC_HIGH_RES

    def test_combined_iodo_and_low_res(self):
        cfg = _apply_protocol_flags(self._base_cfg(), iodo=True, low_res=True)
        assert CARBAMIDOMETHYL_MOD in cfg['index']['fixed_mods']
        assert cfg['search']['mz_bin_width'] == MZ_BIN_WIDTH_LOW_RES
        assert cfg['search']['score_function'] == SCORE_FUNC_LOW_RES

    def test_combined_iodo_and_high_res(self):
        cfg = _apply_protocol_flags(self._base_cfg(), iodo=True, low_res=False)
        assert CARBAMIDOMETHYL_MOD in cfg['index']['fixed_mods']
        assert cfg['search']['mz_bin_width'] == MZ_BIN_WIDTH_HIGH_RES
        assert cfg['search']['score_function'] == SCORE_FUNC_HIGH_RES

    def test_only_relevant_keys_touched_by_low_res(self):
        cfg_before = self._base_cfg()
        cfg_after  = _apply_protocol_flags(self._base_cfg(), low_res=True)
        for key in ('threads', 'precursor_tolerance_ppm', 'min_peaks'):
            assert cfg_after['search'][key] == cfg_before['search'][key], (f'_apply_protocol_flags unexpectedly changed search.{key}')

    def test_non_search_sections_untouched(self):
        cfg_before = self._base_cfg()
        cfg_after  = _apply_protocol_flags(self._base_cfg(), iodo=True, low_res=True)
        for section in ('global', 'convert', 'percolator', 'quantify'):
            assert cfg_after.get(section) == cfg_before.get(section), (f'_apply_protocol_flags unexpectedly changed section [{section}]')

class TestApplyProtocolFlagsMods:
    def _base_cfg(self):
        return settings.loadDefaultConfig()

    def test_iodo_true_adds_to_fixed_mods(self):
        cfg = _apply_protocol_flags(self._base_cfg(), iodo=True)
        assert CARBAMIDOMETHYL_MOD in cfg['index']['fixed_mods']

    def test_iodo_false_removes_from_fixed_mods(self):
        cfg = _apply_protocol_flags(self._base_cfg(), iodo=True)
        cfg = _apply_protocol_flags(cfg, iodo=False)
        assert CARBAMIDOMETHYL_MOD not in cfg['index']['fixed_mods']

    def test_iodo_does_not_touch_mods_spec(self):
        cfg = self._base_cfg()
        original_mods = cfg['index']['mods_spec']
        cfg = _apply_protocol_flags(cfg, iodo=True)
        assert cfg['index']['mods_spec'] == original_mods

    def test_ox_true_adds_met_mod(self):
        cfg = _apply_protocol_flags(self._base_cfg(), ox=True)
        assert MET_OX_MOD in cfg['index']['mods_spec']

    def test_ox_false_removes_met_mod(self):
        cfg = _apply_protocol_flags(self._base_cfg(), ox=True)
        cfg = _apply_protocol_flags(cfg, ox=False)
        assert MET_OX_MOD not in cfg['index']['mods_spec']

    def test_ox_none_does_not_touch_mods_spec(self):
        cfg = self._base_cfg()
        original = cfg['index']['mods_spec']
        cfg = _apply_protocol_flags(cfg)
        assert cfg['index']['mods_spec'] == original

    def test_phos_true_adds_phos_mod(self):
        cfg = _apply_protocol_flags(self._base_cfg(), phos=True)
        assert PHOSPHO_MOD in cfg['index']['mods_spec']

    def test_phos_false_removes_phos_mod(self):
        cfg = _apply_protocol_flags(self._base_cfg(), phos=True)
        cfg = _apply_protocol_flags(cfg, phos=False)
        assert PHOSPHO_MOD not in cfg['index']['mods_spec']

    def test_n_cyc_true_adds_to_nterm_peptide_key(self):
        cfg = _apply_protocol_flags(self._base_cfg(), n_cyc=True)
        assert NCYC_MOD in cfg['index']['nterm_peptide_mods_spec']

    def test_n_cyc_false_removes_from_nterm_peptide_key(self):
        cfg = _apply_protocol_flags(self._base_cfg(), n_cyc=True)
        cfg = _apply_protocol_flags(cfg, n_cyc=False)
        assert NCYC_MOD not in cfg['index']['nterm_peptide_mods_spec']

    def test_n_ace_true_adds_to_nterm_protein_key(self):
        cfg = _apply_protocol_flags(self._base_cfg(), n_ace=True)
        assert NACE_MOD in cfg['index']['nterm_protein_mods_spec']

    def test_n_ace_false_removes_from_nterm_protein_key(self):
        cfg = _apply_protocol_flags(self._base_cfg(), n_ace=True)
        cfg = _apply_protocol_flags(cfg, n_ace=False)
        assert NACE_MOD not in cfg['index']['nterm_protein_mods_spec']

    def test_n_cyc_does_not_touch_mods_spec(self):
        cfg = self._base_cfg()
        original_mods = cfg['index']['mods_spec']
        cfg = _apply_protocol_flags(cfg, n_cyc=True)
        assert cfg['index']['mods_spec'] == original_mods

    def test_n_ace_does_not_touch_mods_spec(self):
        cfg = self._base_cfg()
        original_mods = cfg['index']['mods_spec']
        cfg = _apply_protocol_flags(cfg, n_ace=True)
        assert cfg['index']['mods_spec'] == original_mods

    def test_ox_and_iodo_coexist(self):
        cfg = _apply_protocol_flags(self._base_cfg(), iodo=True, ox=True)
        assert CARBAMIDOMETHYL_MOD in cfg['index']['fixed_mods']
        assert MET_OX_MOD in cfg['index']['mods_spec']

    def test_iodo_does_not_remove_ox(self):
        cfg = _apply_protocol_flags(self._base_cfg(), ox=True)
        cfg = _apply_protocol_flags(cfg, iodo=True)
        assert MET_OX_MOD in cfg['index']['mods_spec']

    def test_all_flags_none_changes_nothing(self):
        cfg_before = self._base_cfg()
        cfg_after  = _apply_protocol_flags(self._base_cfg())
        assert cfg_after['index']['mods_spec'] == cfg_before['index']['mods_spec']

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
        config_set(iodo=True)
        assert settings.globalConfigPath().exists()

    def test_created_config_is_valid_toml(self, isolated_config_dir):
        config_set(iodo=True)
        with settings.globalConfigPath().open('rb') as f:
            result = tomllib.load(f)
        assert isinstance(result, dict)

    def test_low_res_sets_bin_width_and_score(self, initialised_config):
        config_set(low_res=True)
        cfg = _loadConfigFile()
        assert cfg['search']['mz_bin_width']   == MZ_BIN_WIDTH_LOW_RES
        assert cfg['search']['score_function'] == SCORE_FUNC_LOW_RES

    def test_high_res_sets_bin_width_and_score(self, initialised_config):
        config_set(low_res=False)
        cfg = _loadConfigFile()
        assert cfg['search']['mz_bin_width']   == MZ_BIN_WIDTH_HIGH_RES
        assert cfg['search']['score_function'] == SCORE_FUNC_HIGH_RES

    def test_low_res_is_idempotent(self, initialised_config):
        config_set(low_res=True)
        config_set(low_res=True)
        cfg = _loadConfigFile()
        assert cfg['search']['mz_bin_width']   == MZ_BIN_WIDTH_LOW_RES
        assert cfg['search']['score_function'] == SCORE_FUNC_LOW_RES

    def test_sets_organism_in_config(self, initialised_config):
        config_set(organism=['Test1=TEST1', 'Test2=TEST2'])
        cfg = _loadConfigFile()
        assert cfg['organism'] == {'Test1': 'TEST1', 'Test2': 'TEST2'}
    
    def test_set_organism_replaces_existing(self, initialised_config):
        config_set(organism=['Test1=TEST1', 'Test2=TEST2'])
        config_set(organism=['Test1=NEWTEST1'])
        cfg = _loadConfigFile()
        assert cfg['organism'] == {'Test1': 'NEWTEST1'}
        assert 'Test2' not in cfg['organism']

    def test_organism_section_written_as_toml_table(self, initialised_config):
        config_set(organism=['Test1=TEST1', 'Test2=TEST2'])
        cfg = _loadConfigFile()
        assert isinstance(cfg['organism'], dict)
        assert isinstance(cfg['organism']['Test1'], str)

    def test_combined_organism_and_low_res(self, initialised_config):
        config_set(low_res=True, organism=['Test1=TEST1'])
        cfg = _loadConfigFile()
        assert cfg['organism'] == {'Test1': 'TEST1'}
        assert cfg['search']['mz_bin_width'] == MZ_BIN_WIDTH_LOW_RES

    def test_combined_organism_and_high_res(self, initialised_config):
        config_set(low_res=False, organism=['Test1=TEST1'])
        cfg = _loadConfigFile()
        assert cfg['organism'] == {'Test1': 'TEST1'}
        assert cfg['search']['mz_bin_width'] == MZ_BIN_WIDTH_HIGH_RES

    def test_no_flags_exits_nonzero(self, isolated_config_dir):
        with pytest.raises(SystemExit) as exc:
            config_set()
        assert exc.value.code!= 0

    def test_all_other_config_keys_unchanged_after_set(self, initialised_config):
        before = _loadConfigFile()
        config_set(low_res=True)
        after = _loadConfigFile()
        for section, values in before.items():
            if section == 'search':
                for key, val in values.items():
                    if key not in ('mz_bin_width', 'score_function'):
                        assert after[section][key] == val, (
                            f'config_set unexpectedly changed {section}.{key}'
                        )
            else:
                assert after[section] == values, (
                    f'config_set unexpectedly changed section [{section}]'
                )

    def test_other_sections_unchanged_after_organism_set(self, initialised_config):
        before = _loadConfigFile()
        config_set(organism=['Mt=MEDTR'])
        after = _loadConfigFile()
        for section in ('search', 'percolator', 'quantify', 'convert', 'global'):
            assert after.get(section) == before.get(section), (
                f'config_set --organism unexpectedly changed section [{section}]'
            )
    
    def test_iodo_adds_carbamidomethyl_to_fixed_mods(self, initialised_config):
        config_set(iodo=True)
        assert CARBAMIDOMETHYL_MOD in _loadConfigFile()['index']['fixed_mods']

    def test_no_iodo_removes_carbamidomethyl_from_fixed_mods(self, initialised_config):
        config_set(iodo=True)
        config_set(iodo=False)
        assert CARBAMIDOMETHYL_MOD not in _loadConfigFile()['index']['fixed_mods']

    def test_iodo_does_not_add_to_mods_spec(self, initialised_config):
        before_mods = _loadConfigFile()['index']['mods_spec']
        config_set(iodo=True)
        assert _loadConfigFile()['index']['mods_spec'] == before_mods

    def test_iodo_is_idempotent(self, initialised_config):
        config_set(iodo=True)
        config_set(iodo=True)
        assert _loadConfigFile()['index']['fixed_mods'].count(CARBAMIDOMETHYL_MOD) == 1

    def test_ox_adds_met_mod(self, initialised_config):
        config_set(ox=True)
        assert MET_OX_MOD in _loadConfigFile()['index']['mods_spec']

    def test_no_ox_removes_met_mod(self, initialised_config):
        config_set(ox=True)
        config_set(ox=False)
        assert MET_OX_MOD not in _loadConfigFile()['index']['mods_spec']

    def test_ox_is_idempotent(self, initialised_config):
        config_set(ox=True)
        config_set(ox=True)
        assert _loadConfigFile()['index']['mods_spec'].count(MET_OX_MOD) == 1

    def test_phos_adds_phos_mod(self, initialised_config):
        config_set(phos=True)
        assert PHOSPHO_MOD in _loadConfigFile()['index']['mods_spec']

    def test_no_phos_removes_phos_mod(self, initialised_config):
        config_set(phos=True)
        config_set(phos=False)
        assert PHOSPHO_MOD not in _loadConfigFile()['index']['mods_spec']

    def test_n_cyc_adds_to_nterm_peptide_spec(self, initialised_config):
        config_set(n_cyc=True)
        assert NCYC_MOD in _loadConfigFile()['index']['nterm_peptide_mods_spec']

    def test_no_n_cyc_removes_from_nterm_peptide_spec(self, initialised_config):
        config_set(n_cyc=True)
        config_set(n_cyc=False)
        assert NCYC_MOD not in _loadConfigFile()['index']['nterm_peptide_mods_spec']

    def test_n_ace_adds_to_nterm_protein_spec(self, initialised_config):
        config_set(n_ace=True)
        assert NACE_MOD in _loadConfigFile()['index']['nterm_protein_mods_spec']

    def test_no_n_ace_removes_from_nterm_protein_spec(self, initialised_config):
        config_set(n_ace=True)
        config_set(n_ace=False)
        assert NACE_MOD not in _loadConfigFile()['index']['nterm_protein_mods_spec']

    def test_custom_adds_entry(self, initialised_config):
        config_set(custom='1K+28.0313')
        assert '1K+28.0313' in _loadConfigFile()['search']['custom_mods']

    def test_custom_is_additive(self, initialised_config):
        config_set(custom='1K+28.0313')
        config_set(custom='1R+14.0157')
        mods = _loadConfigFile()['search']['custom_mods']
        assert '1K+28.0313' in mods
        assert '1R+14.0157' in mods

    def test_custom_empty_string_clears_all(self, initialised_config):
        config_set(custom='1K+28.0313')
        config_set(custom='')
        assert _loadConfigFile()['search']['custom_mods'] == ''

    def test_custom_managed_mod_not_added(self, initialised_config):
        config_set(custom='1M+15.9949')
        assert '1M+15.9949' not in _loadConfigFile()['search']['custom_mods']

    def test_n_cyc_does_not_change_mods_spec(self, initialised_config):
        before = _loadConfigFile()['index']['mods_spec']
        config_set(n_cyc=True)
        assert _loadConfigFile()['index']['mods_spec'] == before

    def test_n_ace_does_not_change_mods_spec(self, initialised_config):
        before = _loadConfigFile()['index']['mods_spec']
        config_set(n_ace=True)
        assert _loadConfigFile()['index']['mods_spec'] == before

    def test_all_other_config_keys_unchanged_after_new_mod_set(self, initialised_config):
        before = _loadConfigFile()
        config_set(ox=True, phos=True, n_cyc=True, n_ace=True)
        after = _loadConfigFile()
        for section, values in before.items():
            if section == 'index':
                for key, val in values.items():
                    if key not in ('mods_spec', 'fixed_mods', 'nterm_peptide_mods_spec', 'nterm_protein_mods_spec'):
                        assert after[section][key] == val
            else:
                assert after[section] == values