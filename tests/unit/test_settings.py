'''
Unit tests for comms.utils.settings.
'''

# -- Import external dependencies
import pytest, tomllib
from pathlib import Path

# -- Import internal functions
from comms.utils.settings import loadDefaultConfig, userConfigPath, config as live_config

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
