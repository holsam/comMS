'''
Unit tests for src/comms/utils/installrdeps.py
'''
import json
from unittest.mock import patch, MagicMock
import pytest

from comms.utils.installrdeps import (
    check_r_dependencies, install_r_dependencies, install_r_dependencies_terminal, _print_dependency_table,
)


class TestCheckRDependencies:
    def test_returns_none_when_rscript_not_on_path(self):
        with patch('shutil.which', return_value=None):
            assert check_r_dependencies() is None

    def test_parses_well_formed_json(self):
        payload = json.dumps({'installed': ['limma'], 'missing': ['iq']})
        with patch('shutil.which', return_value='/usr/bin/Rscript'), \
             patch('subprocess.run', return_value=MagicMock(returncode=0, stdout=payload, stderr='')):
            result = check_r_dependencies()
        assert result == {'installed': ['limma'], 'missing': ['iq']}

    def test_nonzero_return_code_returns_none(self):
        with patch('shutil.which', return_value='/usr/bin/Rscript'), \
             patch('subprocess.run', return_value=MagicMock(returncode=1, stdout='', stderr='boom')):
            assert check_r_dependencies() is None

    def test_malformed_json_returns_none(self):
        with patch('shutil.which', return_value='/usr/bin/Rscript'), \
             patch('subprocess.run', return_value=MagicMock(returncode=0, stdout='not json', stderr='')):
            assert check_r_dependencies() is None


class TestPrintDependencyTable:
    def test_only_installed_line_when_nothing_missing(self, caplog):
        import logging
        with caplog.at_level(logging.INFO):
            _print_dependency_table({'installed': ['limma'], 'missing': []})
        assert 'Installed' in caplog.text and 'Missing' not in caplog.text

    def test_both_lines_when_something_missing(self, caplog):
        import logging
        with caplog.at_level(logging.INFO):
            _print_dependency_table({'installed': ['limma'], 'missing': ['iq']})
        assert 'Missing' in caplog.text
        assert 'r-utils install' in caplog.text

    def test_neither_line_when_both_empty(self, caplog):
        import logging
        with caplog.at_level(logging.INFO):
            _print_dependency_table({'installed': [], 'missing': []})
        assert caplog.text == ''


class TestInstallRDependencies:
    def test_returns_false_when_rscript_not_on_path(self):
        with patch('shutil.which', return_value=None):
            assert install_r_dependencies() is False

    def test_streams_stdout_lines(self, caplog):
        import logging
        proc = MagicMock()
        proc.stdout = iter(['installing limma...\n', 'done\n'])
        proc.returncode = 0
        with patch('shutil.which', return_value='/usr/bin/Rscript'), \
             patch('subprocess.Popen', return_value=proc), caplog.at_level(logging.INFO):
            result = install_r_dependencies()
        assert result is True
        assert 'installing limma' in caplog.text

    def test_nonzero_exit_returns_false(self):
        proc = MagicMock()
        proc.stdout = iter([])
        proc.returncode = 1
        with patch('shutil.which', return_value='/usr/bin/Rscript'), patch('subprocess.Popen', return_value=proc):
            assert install_r_dependencies() is False


class TestInstallRDependenciesTerminal:
    def test_nothing_missing_informs_without_prompting(self, caplog):
        import logging
        payload = json.dumps({'installed': ['limma'], 'missing': []})
        with patch('shutil.which', return_value='/usr/bin/Rscript'), \
             patch('subprocess.run', return_value=MagicMock(returncode=0, stdout=payload, stderr='')), \
             caplog.at_level(logging.INFO):
            install_r_dependencies_terminal()
        assert 'No dependencies missing' in caplog.text

    def test_missing_and_user_confirms_installs(self):
        payload = json.dumps({'installed': [], 'missing': ['iq']})
        with patch('shutil.which', return_value='/usr/bin/Rscript'), \
             patch('subprocess.run', return_value=MagicMock(returncode=0, stdout=payload, stderr='')), \
             patch('comms.utils.installrdeps.logMsg.input', return_value='y'), \
             patch('comms.utils.installrdeps.install_r_dependencies') as mock_install:
            install_r_dependencies_terminal()
        mock_install.assert_called_once()

    def test_missing_and_user_declines_cancels(self):
        payload = json.dumps({'installed': [], 'missing': ['iq']})
        with patch('shutil.which', return_value='/usr/bin/Rscript'), \
             patch('subprocess.run', return_value=MagicMock(returncode=0, stdout=payload, stderr='')), \
             patch('comms.utils.installrdeps.logMsg.input', return_value='n'), \
             patch('comms.utils.installrdeps.install_r_dependencies') as mock_install:
            install_r_dependencies_terminal()
        mock_install.assert_not_called()

    def test_malformed_output_logs_error_without_raising(self, caplog):
        import logging
        with patch('shutil.which', return_value='/usr/bin/Rscript'), \
             patch('subprocess.run', return_value=MagicMock(returncode=0, stdout='not json', stderr='')), \
             caplog.at_level(logging.ERROR):
            install_r_dependencies_terminal()   # should not raise