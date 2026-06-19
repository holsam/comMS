'''
Integration tests for src/comms/commands/convert.py > run_convert()
'''

# -- Import external dependencies
import logging, pytest
from pathlib import Path

# -- Import internal functions
from comms.commands.convert import run_convert
from comms.utils.log import logMsg
from tests.integration.test_trfp import REAL_RAW_FIXTURE

# -- Define pytest mark
pytestmark = pytest.mark.trfp

# -- Define test class for no input files found
class TestRunConvertNoFiles:
    def test_handles_non_raw_files_gracefully(self, trfp_exe, tmp_path, experiment_ctx, caplog):
        '''
        Passing a non-.RAW file should trigger the 'no .RAW files' warning and return without raising, since the file is filtered out before TRFP runs
        '''
        dummy = tmp_path / 'not_raw.mzML'
        dummy.touch()
        with caplog.at_level(logging.WARNING):
            run_convert(data_files=[dummy], ctx=experiment_ctx, gzip=False)
        assert 'No .RAW files' in caplog.text

class TestRunConvertInvalidFile:
    def test_reports_failure_for_invalid_raw(self, trfp_exe, tmp_path, experiment_ctx, caplog):
        fake = tmp_path / 'fake.RAW'
        fake.write_bytes(b'NOTRAW\x00\x01')
        with caplog.at_level(logging.INFO):
            run_convert(data_files=[fake], ctx=experiment_ctx, gzip=False)
        # TRFP exits non-zero; the completion summary must report at least one failure.
        assert '0 succeeded' in caplog.text or 'failed' in caplog.text

@pytest.mark.skipif(
    not REAL_RAW_FIXTURE.exists(),
    reason=(f'No real .RAW fixture at {REAL_RAW_FIXTURE}. Place a valid Thermo .RAW file there to enable this test.'),
)

# -- Define test class for converting real .RAW file
class TestRunConvertRealFile:
    def test_creates_output_directory(self, trfp_exe, tmp_path, experiment_ctx):
        run_convert(data_files=[REAL_RAW_FIXTURE], ctx=experiment_ctx, gzip=False)
        expected_dir = tmp_path / 'comms' / 'results' / 'convert'
        assert expected_dir.exists()

    def test_produces_mzml_output(self, trfp_exe, tmp_path, experiment_ctx):
        run_convert(data_files=[REAL_RAW_FIXTURE], ctx=experiment_ctx, gzip=False)
        out_dir = tmp_path / 'comms' / 'results' / 'convert'
        mzml_files = list(out_dir.glob('*.mzML'))
        assert mzml_files, 'run_convert produced no .mzML files'

    def test_summary_reports_success(self, trfp_exe, tmp_path, experiment_ctx, caplog):
        with caplog.at_level(logging.INFO):
            run_convert(data_files=[REAL_RAW_FIXTURE], ctx=experiment_ctx, gzip=False)
        assert 'succeeded' in caplog.text