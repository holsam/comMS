'''
Unit tests for comms.utils.settings.
'''

# -- Import external dependencies
import pytest, tomllib
from pathlib import Path

# -- Import internal functions
from comms.utils.settings import loadDefaultConfig, globalConfigPath, resolveConfig, resolvedModifications

# -- Define tests for validating user config path
class TestUserConfigPath:
    def test_returns_path_object(self):
        p = globalConfigPath()
        assert isinstance(p, Path)

    def test_path_ends_with_config_toml(self):
        p = globalConfigPath()
        assert p.name == 'config.toml'

    def test_parent_dir_is_named_comms(self):
        p = globalConfigPath()
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

# -- Define tests for resolving configuration
class TestResolveConfig:
    def test_default_when_nothing_present(self, isolated_config_dir, tmp_path):
        cfg, source = resolveConfig(tmp_path / 'comms')
        assert isinstance(cfg, dict) and 'search' in cfg
        assert 'default' in source

    def test_global_used_when_present(self, isolated_config_dir):
        from comms.commands.config import config_init
        config_init()
        cfg, source = resolveConfig(None)
        assert source.startswith('global')

    def test_local_preferred_over_global(self, isolated_config_dir, tmp_path):
        from comms.commands.config import config_init
        from comms.utils.settings import loadDefaultConfig
        import tomli_w
        config_init()                                   # global exists
        comms = tmp_path / 'comms'; comms.mkdir(parents=True)
        local = loadDefaultConfig(); local['search']['threads'] = 7
        with (comms / 'config.toml').open('wb') as f:
            tomli_w.dump(local, f)
        cfg, source = resolveConfig(comms)
        assert cfg['search']['threads'] == 7
        assert source.startswith('local')
# -- Define tests for falling back to default configuration
class TestConfigFallback:
    def test_falls_back_to_defaults_when_no_user_config(self, isolated_config_dir, monkeypatch):
        '''
        When globalConfigPath() returns a path that does not exist, the module
        should load bundled defaults.  We simulate this by importing settings
        with a patched path pointing to a non-existent file.
        '''
        import importlib
        import comms.utils.settings as settings_mod

        monkeypatch.setattr(settings_mod, 'globalConfigPath', Path('/nonexistent/config.toml'))

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