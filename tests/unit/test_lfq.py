'''
Unit tests for src/comms/commands/lfq.py _groupPsmsByFraction helper function
'''
# -- Import external dependencies
import logging, pytest
import pandas as pd
from pathlib import Path

# -- Import internal dependencies
from comms.commands.lfq import _groupPsmsByFraction

# -- Define helper functions
# -- _make_samples: return a minimal samples DataFrame
def _make_samples(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)

# -- _make_psm_files: write dummy PSM files and return their Paths
def _make_psm_files(tmp_path: Path, stems: list[str]) -> list[Path]:
    psm_dir = tmp_path / 'rescore'
    psm_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for stem in stems:
        p = psm_dir / f'{stem}.percolator.target.psms.txt'
        p.touch()
        paths.append(p)
    return paths

# -- Define tests for _groupPsmsByFraction
class TestGroupPsmsByFraction:
    def test_returns_dict(self, tmp_path):
        samples = _make_samples([
            {'raw_file': 'sample_a.RAW', 'fraction': 'WCL'},
        ])
        psm_files = _make_psm_files(tmp_path, ['sample_a'])
        result = _groupPsmsByFraction(psm_files, samples)
        assert isinstance(result, dict)

    def test_groups_three_fractions_correctly(self, tmp_path):
        samples = _make_samples([
            {'raw_file': 'mock_wcl.RAW',  'fraction': 'WCL'},
            {'raw_file': 'treat_wcl.RAW', 'fraction': 'WCL'},
            {'raw_file': 'mock_ecf.RAW',  'fraction': 'ECF'},
            {'raw_file': 'treat_ecf.RAW', 'fraction': 'ECF'},
            {'raw_file': 'mock_pur.RAW',   'fraction': 'PUR'},
            {'raw_file': 'treat_pur.RAW',  'fraction': 'PUR'},
        ])
        psm_files = _make_psm_files(
            tmp_path,
            ['mock_wcl', 'treat_wcl', 'mock_ecf', 'treat_ecf', 'mock_pur', 'treat_pur'],
        )
        result = _groupPsmsByFraction(psm_files, samples)
        assert set(result.keys()) == {'WCL', 'ECF', 'PUR'}

    def test_each_fraction_contains_correct_files(self, tmp_path):
        samples = _make_samples([
            {'raw_file': 'mock_wcl.RAW',  'fraction': 'WCL'},
            {'raw_file': 'treat_wcl.RAW', 'fraction': 'WCL'},
            {'raw_file': 'mock_pur.RAW',   'fraction': 'PUR'},
        ])
        psm_files = _make_psm_files(tmp_path, ['mock_wcl', 'treat_wcl', 'mock_pur'])
        result = _groupPsmsByFraction(psm_files, samples)
        assert len(result['WCL']) == 2
        assert len(result['PUR']) == 1

    def test_values_are_lists_of_paths(self, tmp_path):
        samples = _make_samples([
            {'raw_file': 'sample_a.RAW', 'fraction': 'WCL'},
        ])
        psm_files = _make_psm_files(tmp_path, ['sample_a'])
        result = _groupPsmsByFraction(psm_files, samples)
        for paths in result.values():
            assert isinstance(paths, list)
            for p in paths:
                assert isinstance(p, Path)

    def test_paths_in_result_match_input_paths(self, tmp_path):
        samples = _make_samples([
            {'raw_file': 'sample_a.RAW', 'fraction': 'WCL'},
            {'raw_file': 'sample_b.RAW', 'fraction': 'WCL'},
        ])
        psm_files = _make_psm_files(tmp_path, ['sample_a', 'sample_b'])
        result = _groupPsmsByFraction(psm_files, samples)
        assert set(result['WCL']) == set(psm_files)

    def test_single_fraction_returns_one_key(self, tmp_path):
        samples = _make_samples([
            {'raw_file': 'sample_a.RAW', 'fraction': 'WCL'},
            {'raw_file': 'sample_b.RAW', 'fraction': 'WCL'},
        ])
        psm_files = _make_psm_files(tmp_path, ['sample_a', 'sample_b'])
        result = _groupPsmsByFraction(psm_files, samples)
        assert list(result.keys()) == ['WCL']

    def test_single_fraction_contains_all_files(self, tmp_path):
        samples = _make_samples([
            {'raw_file': 'sample_a.RAW', 'fraction': 'WCL'},
            {'raw_file': 'sample_b.RAW', 'fraction': 'WCL'},
        ])
        psm_files = _make_psm_files(tmp_path, ['sample_a', 'sample_b'])
        result = _groupPsmsByFraction(psm_files, samples)
        assert len(result['WCL']) == 2

    def test_single_fraction_still_returns_dict(self, tmp_path):
        samples = _make_samples([
            {'raw_file': 'sample_a.RAW', 'fraction': 'WCL'},
        ])
        psm_files = _make_psm_files(tmp_path, ['sample_a'])
        result = _groupPsmsByFraction(psm_files, samples)
        assert isinstance(result, dict)

    def test_unmatched_file_is_excluded_from_result(self, tmp_path):
        samples = _make_samples([
            {'raw_file': 'known_sample.RAW', 'fraction': 'WCL'},
        ])
        psm_files = _make_psm_files(tmp_path, ['known_sample', 'unknown_sample'])
        result = _groupPsmsByFraction(psm_files, samples)
        all_files = [f for files in result.values() for f in files]
        names = [f.name for f in all_files]
        assert not any('unknown_sample' in n for n in names)
        assert 'WCL' in result
        assert len(result['WCL']) == 1

    def test_all_files_unmatched_returns_empty_dict(self, tmp_path):
        samples = _make_samples([
            {'raw_file': 'different_name.RAW', 'fraction': 'WCL'},
        ])
        psm_files = _make_psm_files(tmp_path, ['unknown_a', 'unknown_b'])
        result = _groupPsmsByFraction(psm_files, samples)
        assert result == {}

    def test_empty_psm_list_returns_empty_dict(self, tmp_path):
        samples = _make_samples([
            {'raw_file': 'sample_a.RAW', 'fraction': 'WCL'},
        ])
        result = _groupPsmsByFraction([], samples)
        assert result == {}

    def test_empty_sample_sheet_returns_empty_dict(self, tmp_path):
        samples = pd.DataFrame(columns=['raw_file', 'fraction'])
        psm_files = _make_psm_files(tmp_path, ['sample_a'])
        result = _groupPsmsByFraction(psm_files, samples)
        assert result == {}
    
    def test_matches_raw_file_with_raw_extension(self, tmp_path):
        samples = _make_samples([
            {'raw_file': 'SAMPLE_A.RAW', 'fraction': 'WCL'},
        ])
        psm_files = _make_psm_files(tmp_path, ['SAMPLE_A'])
        result = _groupPsmsByFraction(psm_files, samples)
        assert 'WCL' in result

    def test_matches_raw_file_with_mzML_extension(self, tmp_path):
        samples = _make_samples([
            {'raw_file': 'SAMPLE_B.mzML', 'fraction': 'ECF'},
        ])
        psm_files = _make_psm_files(tmp_path, ['SAMPLE_B'])
        result = _groupPsmsByFraction(psm_files, samples)
        assert 'ECF' in result

    def test_matches_raw_file_without_extension(self, tmp_path):
        '''raw_file column without extension should match PSM stem directly.'''
        samples = _make_samples([
            {'raw_file': 'SAMPLE_C', 'fraction': 'PUR'},
        ])
        psm_files = _make_psm_files(tmp_path, ['SAMPLE_C'])
        result = _groupPsmsByFraction(psm_files, samples)
        assert 'PUR' in result