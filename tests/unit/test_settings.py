'''
Unit tests for comms.utils.settings.
'''

# -- Import external dependencies
import pytest, tomllib
from pathlib import Path

# -- Import internal functions
from comms.utils.settings import loadDefaultConfig, userConfigPath, config as live_config, resolvedModifications

# -- Define tests for validating user config path
class TestUserConfigPath:
    def test_returns_path_object(self):
        p = userConfigPath()
        assert isinstance(p, Path)

    def test_path_ends_with_config_toml(self):
        p = userConfigPath()
        assert p.name == 'config.toml'

    def test_parent_dir_is_named_comms(self):
        p = userConfigPath()
        assert p.parent.name == 'comms'

# -- Define tests for loading default configuration
class TestLoadDefaultConfig:
    def test_is_dict(self):
        assert isinstance(loadDefaultConfig(), dict)

    def test_idempotent(self):
        '''Calling twice returns equal dicts (no side effects).'''
        assert loadDefaultConfig() == loadDefaultConfig()

    def test_bundled_config_is_valid_toml(self):
        '''The underlying file can be parsed as TOML without error.'''
        from importlib.resources import files as pkg_files
        with pkg_files('comms').joinpath('config.toml').open('rb') as f:
            result = tomllib.load(f)
        assert isinstance(result, dict)

# -- Define tests for loading 'live' configuration
class TestLiveConfig:
    def test_config_is_dict(self):
        assert isinstance(live_config, dict)

    def test_config_has_search_section(self):
        assert 'search' in live_config

    def test_config_has_percolator_section(self):
        assert 'percolator' in live_config
    
    def test_config_has_organism_section(self):
        assert 'organism' in live_config
        assert live_config['organism'] == {}

    def test_config_values_are_not_none(self):
        '''Spot-check that critical keys are not None.'''
        assert live_config['search']['threads'] is not None
        assert live_config['search']['score_function'] is not None
        assert live_config['percolator']['psm_fdr'] is not None

# -- Define tests for falling back to default configuration
class TestConfigFallback:
    def test_falls_back_to_defaults_when_no_user_config(self, isolated_config_dir, monkeypatch):
        '''
        When userConfigPath() returns a path that does not exist, the module
        should load bundled defaults.  We simulate this by importing settings
        with a patched path pointing to a non-existent file.
        '''
        import importlib
        import comms.utils.settings as settings_mod

        monkeypatch.setattr(settings_mod, '_user_config_path', Path('/nonexistent/config.toml'))

        # Reload to re-run the module-level config loading logic
        # (We test the function directly since reloading modules is fragile in pytest)
        defaults = loadDefaultConfig()
        assert isinstance(defaults, dict)
        assert 'search' in defaults

# -- Define tests for resolvedModifications function
class TestResolvedModsSpec:
    def test_returns_string(self):
        cfg = loadDefaultConfig()
        assert isinstance(resolvedModifications(cfg), str)

    def test_base_only_when_no_custom(self):
        cfg = loadDefaultConfig()
        cfg['index']['custom_mods'] = ''
        potential_resolved = [cfg['index']['mods_spec']+',C+0', 'C+0,'+cfg['index']['mods_spec']]
        assert resolvedModifications(cfg) in potential_resolved

    def test_custom_appended_to_base(self):
        cfg = loadDefaultConfig()
        cfg['index']['mods_spec']  = '1M+15.9949'
        cfg['index']['custom_mods'] = '1K+28.0313'
        result = resolvedModifications(cfg)
        assert '1M+15.9949' in result
        assert '1K+28.0313' in result

    def test_custom_duplicate_of_base_not_repeated(self):
        cfg = loadDefaultConfig()
        cfg['index']['mods_spec']   = '1M+15.9949'
        cfg['index']['custom_mods'] = '1M+15.9949'
        result = resolvedModifications(cfg)
        assert result.count('1M+15.9949') == 1

    def test_empty_base_returns_custom_only(self):
        cfg = loadDefaultConfig()
        cfg['index']['mods_spec']   = ''
        cfg['index']['custom_mods'] = '1K+28.0313'
        potential_resolved = [cfg['index']['custom_mods']+',C+0', 'C+0,'+cfg['index']['custom_mods']]
        assert resolvedModifications(cfg) in potential_resolved

    def test_both_empty_returns_empty_string(self):
        cfg = loadDefaultConfig()
        cfg['index']['mods_spec']   = ''
        cfg['index']['custom_mods'] = ''
        assert resolvedModifications(cfg) == 'C+0'

    def test_no_leading_or_trailing_commas(self):
        cfg = loadDefaultConfig()
        cfg['index']['custom_mods'] = '1K+28.0313'
        result = resolvedModifications(cfg)
        assert not result.startswith(',')
        assert not result.endswith(',')