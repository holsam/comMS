'''
Integration tests for src/comms/utils/trfp.py
'''

# -- Import external dependencies

import os, pytest, sys
from pathlib import Path

# -- Import internal functions
from comms.utils.trfp import findTRFP, convertRaw

# -- Define pytest mark for trfp (all tests in file require TRFP)
pytestmark = pytest.mark.trfp

# -- Define constant path to real .RAW file fixture
REAL_RAW_FIXTURE = Path(__file__).parent.parent / 'fixtures' / 'real_sample.RAW'

# -- Define tests for locating ThermoRawFileParser binary
class TestFindTRFP:
    def test_returns_path_to_existing_exe(self, trfp_exe):
        assert trfp_exe.exists()

    def test_path_ends_with_exe(self, trfp_exe):
        assert trfp_exe.suffix == '.exe'

    def test_returns_none_for_empty_dir(self, tmp_path):
        result = findTRFP(tmp_path)
        assert result is None

    def test_returns_none_for_nonexistent_dir(self, tmp_path):
        result = findTRFP(tmp_path / 'nonexistent')
        assert result is None

# -- Define test for failing to converting .RAW file due to invalid file
class TestConvertRawFailure:
    @pytest.mark.skipif(sys.platform == 'win32', reason='Mono not required on Windows')
    def test_returns_false_on_invalid_raw_file(self, trfp_exe, tmp_path):
        '''
        A file that is not a valid .RAW binary should cause TRFP to exit
        non-zero, which convertRaw should return as False.
        '''
        fake_raw = tmp_path / 'fake.RAW'
        fake_raw.write_bytes(b'NOT A THERMO RAW FILE\x00\x01\x02')
        out_dir = tmp_path / 'mzml'
        result = convertRaw(
            exe_path=trfp_exe,
            raw_file=fake_raw,
            out_dir=out_dir,
            log_path=tmp_path / 'convert.log',
        )
        assert result is False, (
            'convertRaw should return False when TRFP exits non-zero'
        )

# Define test for converting .RAW file
@pytest.mark.skipif(
    not REAL_RAW_FIXTURE.exists(),
    reason=(
        f'No real .RAW fixture found at {REAL_RAW_FIXTURE}. '
        'Place a valid Thermo .RAW file there to enable this test.'
    ),
)
class TestConvertRawRealFile:
    def test_produces_mzml_file(self, trfp_exe, tmp_path):
        out_dir = tmp_path / 'mzml'
        ok = convertRaw(
            exe_path=trfp_exe,
            raw_file=REAL_RAW_FIXTURE,
            out_dir=out_dir,
            gzip=False,
            log_path=tmp_path / 'convert.log',
        )
        assert ok, 'convertRaw returned False — check convert.log'
        mzml_files = list(out_dir.glob('*.mzML'))
        assert mzml_files, 'No .mzML file produced in output directory'

    def test_produced_mzml_is_non_empty(self, trfp_exe, tmp_path):
        out_dir = tmp_path / 'mzml'
        convertRaw(
            exe_path=trfp_exe,
            raw_file=REAL_RAW_FIXTURE,
            out_dir=out_dir,
            gzip=False,
        )
        for mzml in out_dir.glob('*.mzML'):
            assert mzml.stat().st_size > 0
