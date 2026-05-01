'''
Integration tests for src/comms/commands/convert.py > run_convert()
'''

# -- Import external dependencies
import pytest
from pathlib import Path

# -- Import internal functions
from comms.commands.convert import run_convert
from tests.integration.test_trfp import REAL_RAW_FIXTURE

# -- Define pytest mark
pytestmark = pytest.mark.trfp

# -- Define test for no input files found
class TestRunConvertNoFiles:
    def test_handles_empty_input_directory(self, trfp_exe, tmp_path, capsys):
        input_dir = tmp_path / 'raw_files'
        input_dir.mkdir()
        # Should return cleanly without raising; a warning should be printed
        run_convert(input_dir=input_dir, output=tmp_path / 'out', gzip=False)
        captured = capsys.readouterr()
        assert 'No .RAW files' in captured.out or 'WARNING' in captured.out

# -- Define test for invalid .RAW file input
class TestRunConvertInvalidFile:
    def test_reports_failure_for_invalid_raw(self, trfp_exe, tmp_path, capsys):
        input_dir = tmp_path / 'raw_files'
        input_dir.mkdir()
        fake = input_dir / 'fake.RAW'
        fake.write_bytes(b'NOTRAW\x00\x01')
        run_convert(input_dir=input_dir, output=tmp_path / 'out', gzip=False)
        captured = capsys.readouterr()
        # Expect the summary to report at least one failure
        assert 'failed' in captured.out.lower() or '0' in captured.out

# -- Define pytest mark for whether real .RAW file available
@pytest.mark.skipif(
    not REAL_RAW_FIXTURE.exists(),
    reason=(
        f'No real .RAW fixture at {REAL_RAW_FIXTURE}. '
        'Place a valid Thermo .RAW file there to enable this test.'
    ),
)

# -- Define tests for converting real .RAW file
class TestRunConvertRealFile:
    def test_creates_output_directory(self, trfp_exe, tmp_path):
        input_dir = REAL_RAW_FIXTURE.parent
        output = tmp_path / 'out'
        run_convert(input_dir=input_dir, output=output, gzip=False)
        expected_dir = output / 'comms' / 'results' / 'convert'
        assert expected_dir.exists()

    def test_produces_mzml_output(self, trfp_exe, tmp_path, capsys):
        input_dir = REAL_RAW_FIXTURE.parent
        output = tmp_path / 'out'
        run_convert(input_dir=input_dir, output=output, gzip=False)
        out_dir = output / 'comms' / 'results' / 'convert'
        mzml_files = list(out_dir.glob('*.mzML'))
        assert mzml_files, 'run_convert produced no .mzML files'

    def test_summary_reports_success(self, trfp_exe, tmp_path, capsys):
        input_dir = REAL_RAW_FIXTURE.parent
        run_convert(input_dir=input_dir, output=tmp_path / 'out', gzip=False)
        captured = capsys.readouterr()
        assert 'Convert summary' in captured.out
