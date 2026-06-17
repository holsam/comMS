'''
Unit tests for src/comms/commands/uninstall.py
'''

# -- Import external dependencies
import pytest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

# -- Import functions under test
from comms.commands.uninstall import (
    _generated_targets, _detect_uninstall_command, run_uninstall,
)
from comms.utils.log import logMsg


class TestGeneratedTargets:
    def test_includes_existing_config(self, isolated_config_dir):
        cfg = isolated_config_dir / 'config.toml'
        cfg.write_text('[global]\nverbose = false\n')
        assert cfg in _generated_targets()

    def test_empty_when_no_config(self, isolated_config_dir):
        # isolated_config_dir creates the dir but no config file
        assert _generated_targets() == []


class TestDetectUninstallCommand:
    def test_detects_uv_tool_install(self):
        with patch('sys.argv', ['/home/u/.local/share/uv/tools/comms/bin/comms']):
            assert _detect_uninstall_command() == 'uv tool uninstall comms'

    def test_detects_pip(self):
        mock_result = CompletedProcess(
            args=['python', '-m', 'pip', 'list'],
            returncode=0,
            stdout=b'Package    Version\n---------- -------\ncomms        1.9.0\npip        23.1.2\n',
            stderr=b'',
        )
        with patch('sys.argv', ['/usr/local/bin/comms']), patch('subprocess.run', return_value=mock_result):
            assert _detect_uninstall_command() == 'pip uninstall comms'

    def test_falls_back_to_unknown(self):
        mock_result = CompletedProcess(
            args=['python', '-m', 'pip', 'list'],
            returncode=0,
            stdout=b'Package    Version\n---------- -------\npip        23.1.2\n',
            stderr=b'',
        )
        with patch('sys.argv', ['/usr/local/bin/comms']), \
             patch('subprocess.run', return_value=mock_result):
            result = _detect_uninstall_command()
            assert result == '(unknown installation method used, uninstall using package manager)'

    def test_falls_back_to_unknown_when_pip_unavailable(self):
        with patch('sys.argv', ['/usr/local/bin/comms']), \
             patch('subprocess.run', side_effect=FileNotFoundError):
            result = _detect_uninstall_command()
            assert result == '(unknown installation method used, uninstall using package manager)'


class TestRunUninstall:
    def test_dry_run_does_not_delete(self, isolated_config_dir):
        cfg = isolated_config_dir / 'config.toml'
        cfg.write_text('[global]\nverbose = false\n')
        run_uninstall(dry_run=True)
        assert cfg.exists()

    def test_force_deletes_config(self, isolated_config_dir):
        cfg = isolated_config_dir / 'config.toml'
        cfg.write_text('[global]\nverbose = false\n')
        run_uninstall(force=True)
        assert not cfg.exists()

    def test_logger_named_uninstall(self, isolated_config_dir):
        run_uninstall(force=True)
        assert logMsg._instance.logger.name == 'uninstall'