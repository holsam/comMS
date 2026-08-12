'''
Unit tests for src/comms/commands/license.py
'''
from unittest.mock import patch
import pytest

from comms.commands.license import printLicense


class TestPrintLicense:
    def test_raises_systemexit_zero(self):
        with patch('pydoc.pager'):
            with pytest.raises(SystemExit) as exc:
                printLicense()
        assert exc.value.code == 0

    def test_reads_license_file_without_raising(self):
        with patch('pydoc.pager') as mock_pager:
            with pytest.raises(SystemExit):
                printLicense()
        mock_pager.assert_called_once()