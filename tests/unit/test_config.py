'''
Unit tests for src/comms/commands/config.py
'''
import tomllib
import pytest
from pathlib import Path
from unittest.mock import patch

from comms.commands.config import (
    _confirm, _loadConfigFile, _flatten, _printTable, _print_diff_summary,
    _resolve_or_create, config_list, config_verify, config_reset, config_set,
)
from comms.utils.settings import loadDefaultConfig, globalConfigPath
from comms.utils.modspec import CARBAMIDOMETHYL_MOD, MET_OX_MOD


class TestFlatten:
    def test_flat_dict_unchanged(self):
        assert _flatten({'a': 1}) == {'a': 1}

    def test_nested_dict_flattened(self):
        assert _flatten({'outer': {'inner': 42}}) == {'outer.inner': 42}

    def test_deeply_nested(self):
        assert _flatten({'a': {'b': {'c': 'x'}}}) == {'a.b.c': 'x'}

    def test_empty_dict(self):
        assert _flatten({}) == {}

    def test_default_config_flattens_without_error(self):
        flat = _flatten(loadDefaultConfig())
        assert isinstance(flat, dict) and len(flat) > 0


class TestPrintTable:
    def test_renders_without_raising_when_matching_defaults(self):
        defaults = loadDefaultConfig()
        _printTable(_flatten(defaults), _flatten(defaults))

    def test_renders_without_raising_with_divergence(self):
        defaults = loadDefaultConfig()
        current = dict(defaults)
        current['search'] = dict(current['search'])
        current['search']['threads'] = 999
        _printTable(_flatten(current), _flatten(defaults))


class TestPrintDiffSummary:
    def test_no_changes_prints_message(self, capsys):
        _print_diff_summary({'a': 1}, {'a': 1})
        assert 'No changes' in capsys.readouterr().out

    def test_changed_key_shows_old_and_new(self, capsys):
        _print_diff_summary({'search.threads': 4}, {'search.threads': 8})
        out = capsys.readouterr().out
        assert '4' in out and '8' in out

    def test_multiple_changes_all_reported(self, capsys):
        _print_diff_summary({'a': 1, 'b': 2}, {'a': 9, 'b': 9})
        out = capsys.readouterr().out
        assert out.count('✓') == 2


class TestResolveOrCreate:
    def test_global_returns_global_path(self, isolated_config_dir):
        assert _resolve_or_create(None, use_global=True) == isolated_config_dir / 'config.toml'

    def test_explicit_path_resolves_to_comms_config(self, tmp_path):
        target = _resolve_or_create(tmp_path, use_global=False)
        assert target == tmp_path / 'comms' / 'config.toml'

    def test_creates_file_from_defaults_if_absent(self, tmp_path):
        target = _resolve_or_create(tmp_path, use_global=False)
        assert target.exists()
        with target.open('rb') as f:
            assert tomllib.load(f) == loadDefaultConfig()

    def test_bare_and_nested_config_both_present_raises(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / 'config.toml').write_text('[search]\n')
        (tmp_path / 'comms').mkdir()
        (tmp_path / 'comms' / 'config.toml').write_text('[search]\n')
        with pytest.raises(SystemExit):
            _resolve_or_create(None, use_global=False)

    def test_prefers_bare_config_when_only_bare_present(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / 'config.toml').write_text('[search]\n')
        target = _resolve_or_create(None, use_global=False)
        assert target == tmp_path / 'config.toml'

    def test_prompts_and_creates_nested_when_neither_present(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with patch('comms.commands.config._confirm', return_value=True):
            target = _resolve_or_create(None, use_global=False)
        assert target == tmp_path / 'comms' / 'config.toml'

    def test_declining_prompt_exits_zero(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with patch('comms.commands.config._confirm', return_value=False):
            with pytest.raises(SystemExit) as exc:
                _resolve_or_create(None, use_global=False)
        assert exc.value.code == 0


class TestConfigList:
    def test_prints_config_path_and_table(self, tmp_path, capsys):
        config_list(tmp_path, False)
        out = capsys.readouterr().out
        assert 'Current config' in out


class TestConfigVerify:
    def test_valid_config_passes(self, tmp_path):
        config_verify(tmp_path, False)   # created from defaults, so valid

    def test_missing_key_exits_nonzero(self, tmp_path):
        target = _resolve_or_create(tmp_path, use_global=False)
        with target.open('rb') as f:
            cfg = tomllib.load(f)
        del cfg['search']['threads']
        import tomli_w
        with target.open('wb') as f:
            tomli_w.dump(cfg, f)
        with pytest.raises(SystemExit):
            config_verify(tmp_path, False)

    def test_unexpected_key_exits_nonzero(self, tmp_path):
        target = _resolve_or_create(tmp_path, use_global=False)
        with target.open('rb') as f:
            cfg = tomllib.load(f)
        cfg['search']['not_a_real_key'] = 1
        import tomli_w
        with target.open('wb') as f:
            tomli_w.dump(cfg, f)
        with pytest.raises(SystemExit):
            config_verify(tmp_path, False)


class TestConfigReset:
    def test_force_resets_without_prompting(self, tmp_path):
        target = _resolve_or_create(tmp_path, use_global=False)
        with target.open('rb') as f:
            cfg = tomllib.load(f)
        cfg['search']['threads'] = 999
        import tomli_w
        with target.open('wb') as f:
            tomli_w.dump(cfg, f)
        config_reset(tmp_path, False, force=True)
        with target.open('rb') as f:
            assert tomllib.load(f) == loadDefaultConfig()

    def test_without_force_prompts_and_only_resets_on_accept(self, tmp_path):
        with patch('comms.commands.config._confirm', return_value=False):
            with pytest.raises(SystemExit) as exc:
                config_reset(tmp_path, False, force=False)
        assert exc.value.code == 0


class TestConfigSet:
    def test_all_none_returns_false_and_no_write(self, tmp_path):
        changed = config_set(tmp_path, False)
        assert changed is False

    def test_protocol_flag_roundtrips(self, tmp_path):
        config_set(tmp_path, False, iodo=True)
        target = tmp_path / 'comms' / 'config.toml'
        with target.open('rb') as f:
            cfg = tomllib.load(f)
        assert CARBAMIDOMETHYL_MOD in cfg['index']['fixed_mods']

    def test_organism_flag_roundtrips(self, tmp_path):
        config_set(tmp_path, False, organism=['Mt=MEDTR'])
        target = tmp_path / 'comms' / 'config.toml'
        with target.open('rb') as f:
            cfg = tomllib.load(f)
        assert cfg['organism'] == {'Mt': 'MEDTR'}

    def test_custom_mod_roundtrips(self, tmp_path):
        config_set(tmp_path, False, custom='1K+28.0313')
        target = tmp_path / 'comms' / 'config.toml'
        with target.open('rb') as f:
            cfg = tomllib.load(f)
        assert '1K+28.0313' in cfg['index']['custom_mods']

    @pytest.mark.parametrize('section, key, flag, value', [
        ('convert', 'gzip', 'gzip', True),
        ('search', 'threads', 'threads', 16),
        ('percolator', 'picked_protein', 'picked_protein', False),
        ('quantify', 'measure', 'measure', 'dNSAF'),
        ('report', 'lfc_threshold', 'lfc_threshold', 2.0),
    ])
    def test_direct_flags_roundtrip(self, tmp_path, section, key, flag, value):
        config_set(tmp_path, False, **{flag: value})
        target = tmp_path / 'comms' / 'config.toml'
        with target.open('rb') as f:
            cfg = tomllib.load(f)
        assert cfg[section][key] == value

    def test_unrelated_sections_untouched(self, tmp_path):
        target = _resolve_or_create(tmp_path, use_global=False)
        with target.open('rb') as f:
            before = tomllib.load(f)
        config_set(tmp_path, False, iodo=True)
        with target.open('rb') as f:
            after = tomllib.load(f)
        for section in ('search', 'percolator', 'quantify', 'convert'):
            assert after.get(section) == before.get(section)

    def test_prints_diff_summary(self, tmp_path, capsys):
        config_set(tmp_path, False, iodo=True)
        assert '✓' in capsys.readouterr().out


class TestConfigSetLocalTarget:
    def test_writes_to_local_path_not_global(self, tmp_path, isolated_config_dir):
        config_set(tmp_path, False, iodo=True)
        assert (tmp_path / 'comms' / 'config.toml').exists()
        assert not globalConfigPath().exists()