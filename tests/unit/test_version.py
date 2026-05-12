'''
Unit tests for src/comms/commands/version.py
'''

# -- Import external dependencies
import pytest
from unittest.mock import patch

# -- Import functions under test
from comms.commands.version import printVersion

# -- Define tests for version command
class TestPrintVersion:
    def test_exits_with_code_zero(self):
        with patch('comms.commands.version.version', return_value='1.2.3'):
            with pytest.raises(SystemExit) as exc:
                printVersion()
        assert exc.value.code == 0

    def test_prints_version_string(self, capsys):
        with patch('comms.commands.version.version', return_value='1.2.3'):
            with pytest.raises(SystemExit):
                printVersion()
        assert '1.2.3' in capsys.readouterr().out

    def test_handles_package_not_found(self, capsys):
        from importlib.metadata import PackageNotFoundError
        with patch('comms.commands.version.version', side_effect=PackageNotFoundError):
            with pytest.raises(SystemExit):
                printVersion()
        assert 'unknown' in capsys.readouterr().out.lower()