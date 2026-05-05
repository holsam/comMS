'''
Unit tests for param-medic helper functions in src/comms/commands/search.py
'''
# -- Import external dependencies
import pytest, statistics
from pathlib import Path
from unittest.mock import MagicMock, patch, call
 
# -- Import functions under test
from comms.commands.search import _parseParamMedicOutput, _runParamMedic
  
# -- Define tests for _parseParamMedicOutput helper function
class TestParseParamMedicOutput: 
    def test_returns_none_tuple_when_file_absent(self, tmp_path):
        pre_tol, bin_wid = _parseParamMedicOutput(tmp_path)
        assert pre_tol is None
        assert bin_wid is None
    def test_parses_well_formed_output(self, tmp_path):
        (tmp_path / 'param-medic.txt').write_text('Precursor error: 8.5 ppm\nFragment error: 0.02 Da\n')
        pre_tol, bin_wid = _parseParamMedicOutput(tmp_path)
        assert pre_tol == 8.5
        assert bin_wid == 0.02
    def test_parses_precursor_only(self, tmp_path):
        (tmp_path / 'param-medic.txt').write_text('Precursor error: 10.0 ppm\n')
        pre_tol, bin_wid = _parseParamMedicOutput(tmp_path)
        assert pre_tol == 10.0
        assert bin_wid is None
    def test_parses_bin_width_only(self, tmp_path):
        (tmp_path / 'param-medic.txt').write_text('Fragment error: 0.05 Da\n')
        pre_tol, bin_wid = _parseParamMedicOutput(tmp_path)
        assert pre_tol is None
        assert bin_wid == 0.05
    def test_returns_none_tuple_for_empty_file(self, tmp_path):
        (tmp_path / 'param-medic.txt').write_text('')
        pre_tol, bin_wid = _parseParamMedicOutput(tmp_path)
        assert pre_tol is None
        assert bin_wid is None
    def test_returns_none_tuple_for_malformed_file(self, tmp_path):
        (tmp_path / 'param-medic.txt').write_text('No useful information here.\n')
        pre_tol, bin_wid = _parseParamMedicOutput(tmp_path)
        assert pre_tol is None
        assert bin_wid is None
    def test_parse_is_case_insensitive(self, tmp_path):
        (tmp_path / 'param-medic.txt').write_text('PRECURSOR tolerance: 12.3 PPM\nFRAGMENT tolerance: 0.01 DA\n')
        pre_tol, bin_wid = _parseParamMedicOutput(tmp_path)
        assert pre_tol == pytest.approx(12.3)
        assert bin_wid == pytest.approx(0.01)
    def test_returns_float_types(self, tmp_path):
        (tmp_path / 'param-medic.txt').write_text('Precursor error: 5.0 ppm\nFragment error: 0.02 Da\n')
        pre_tol, bin_wid = _parseParamMedicOutput(tmp_path)
        assert isinstance(pre_tol, float)
        assert isinstance(bin_wid, float)

# -- _make_mzml_files: helper function returning Paths to empty mzML files
def _make_mzml_files(tmp_path: Path, n: int) -> list[Path]:
    '''Write n empty placeholder mzML files and return their paths.'''
    files = []
    for i in range(n):
        p = tmp_path / f'sample_{i}.mzML'
        p.touch()
        files.append(p)
    return files
 
 # -- Define tests for _runParamMedic helper function
class TestRunParamMedic:
    def _run(self, tmp_path, parse_return_values):
        '''
        Helper: mock paramMedic and _parseParamMedicOutput, run _runParamMedic,
        and return (precursor_tol, mz_bin_width).
        '''
        mzml_files = _make_mzml_files(tmp_path, len(parse_return_values))
        crux_bin = MagicMock()
        out_dir = tmp_path / 'comms' / 'results' / 'search'
        out_dir.mkdir(parents=True)
        with patch('comms.commands.search.cruxutil.paramMedic', return_value=True), \
             patch('comms.commands.search._parseParamMedicOutput', side_effect=parse_return_values):
            return _runParamMedic(crux_bin, mzml_files, out_dir)
    def test_single_file_returns_that_value(self, tmp_path):
        pre_tol, bin_wid = self._run(tmp_path, [(8.0, 0.02)])
        assert pre_tol == 8.0
        assert bin_wid == 0.02
    def test_odd_number_of_files_returns_middle_value(self, tmp_path):
        mocked_outputs = [(5.0, 0.01), (8.0, 0.02), (11.0, 0.03)]
        pre_tol, bin_wid = self._run(tmp_path, mocked_outputs)
        pre_med = statistics.median(i[0] for i in mocked_outputs)
        bin_med = statistics.median(i[1] for i in mocked_outputs)
        assert pre_tol == pre_med
        assert bin_wid == bin_med
    def test_even_number_of_files_returns_average_of_middle_two(self, tmp_path):
        # Expected precusor: 7.0; expected bin width: 0.015
        mocked_outputs = [(4.0, 0.01), (6.0, 0.01), (8.0, 0.02), (10.0, 0.02)]
        pre_tol, bin_wid = self._run(tmp_path, mocked_outputs)
        pre_med = statistics.median(i[0] for i in mocked_outputs)
        bin_med = statistics.median(i[1] for i in mocked_outputs)
        assert pre_tol == pre_med
        assert bin_wid == bin_med
    def test_all_files_returning_none_gives_none_none(self, tmp_path):
        pre_tol, bin_wid = self._run(tmp_path, [(None, None), (None, None), (None, None)])
        assert pre_tol is None
        assert bin_wid is None
    def test_mixed_none_and_valid_excludes_none_from_median(self, tmp_path):
        # Only [6.0, 10.0] contribute so median = 8.0 and 0.03
        mocked_outputs = [(None, None), (6.0, 0.02), (10.0, 0.04)]
        pre_tol, bin_wid = self._run(tmp_path, mocked_outputs)
        pre_med = statistics.median(i[0] for i in mocked_outputs if i[0] is not None)
        bin_med = statistics.median(i[1] for i in mocked_outputs if i[1] is not None)
        assert pre_tol == pre_med
        assert bin_wid == bin_med
    def test_returns_none_precursor_when_all_prec_estimates_are_none(self, tmp_path):
        pre_tol, _ = self._run(tmp_path, [(None, 0.02), (None, 0.04)])
        assert pre_tol is None
    def test_returns_none_bin_width_when_all_bw_estimates_are_none(self, tmp_path):
        _, bin_wid = self._run(tmp_path, [(5.0, None), (9.0, None)])
        assert bin_wid is None
    def test_param_medic_called_once_per_file(self, tmp_path):
        mzml_files = _make_mzml_files(tmp_path, 3)
        crux_bin = MagicMock()
        out_dir = tmp_path / 'comms' / 'results' / 'search'
        out_dir.mkdir(parents=True)
        with patch('comms.commands.search.cruxutil.paramMedic', return_value=True) as mock_pm, patch('comms.commands.search._parseParamMedicOutput', return_value=(5.0, 0.02)):
            _runParamMedic(crux_bin, mzml_files, out_dir)
        assert mock_pm.call_count == 3
    def test_param_medic_failure_excluded_from_estimates(self, tmp_path):
        '''
        If paramMedic returns False for a file, that file should not
        contribute to the median estimate.
        '''
        mzml_files = _make_mzml_files(tmp_path, 3)
        crux_bin = MagicMock()
        out_dir = tmp_path / 'comms' / 'results' / 'search'
        out_dir.mkdir(parents=True)
        # Second file fails; only first and third contribute: median([4.0, 8.0]) = 6.0
        pm_side_effects = [True, False, True]
        parse_side_effects = [(4.0, 0.01), (8.0, 0.02)]
        with patch('comms.commands.search.cruxutil.paramMedic', side_effect=pm_side_effects), patch('comms.commands.search._parseParamMedicOutput', side_effect=parse_side_effects):
            pre_tol, bin_wid = _runParamMedic(crux_bin, mzml_files, out_dir)
        pre_med = statistics.median(i[0] for i in parse_side_effects)
        bin_med = statistics.median(i[1] for i in parse_side_effects)
        assert pre_tol == pre_med
        assert bin_wid == bin_med
    def test_per_file_output_dirs_are_created(self, tmp_path):
        '''Each file should get its own param-medic output subdirectory.'''
        mzml_files = _make_mzml_files(tmp_path, 2)
        crux_bin = MagicMock()
        out_dir = tmp_path / 'comms' / 'results' / 'search'
        out_dir.mkdir(parents=True)
        with patch('comms.commands.search.cruxutil.paramMedic', return_value=True), patch('comms.commands.search._parseParamMedicOutput', return_value=(5.0, 0.02)):
            _runParamMedic(crux_bin, mzml_files, out_dir)
        pm_base = out_dir.parent / 'param-medic'
        for mzml_file in mzml_files:
            assert (pm_base / mzml_file.stem).exists()