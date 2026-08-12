'''
Unit tests for src/comms/utils/samples.py
'''

# -- Import external dependencies
import pytest
import pandas as pd
from pathlib import Path

# -- Import internal functions
from comms.utils.samples import loadSampleSheet, getSamplesByTreatment, getSamplesByFraction, getRawFileMap, REQUIRED_COLUMNS

# -- Define tests for loading sample sheet
class TestLoadSampleSheet:
    def test_loads_valid_tsv(self, sample_sheet_factory):
        df = loadSampleSheet(sample_sheet_factory(['WCL']))
        assert isinstance(df, pd.DataFrame)

    def test_returns_correct_row_count(self, sample_sheet_factory):
        df = loadSampleSheet(sample_sheet_factory(['WCL']))
        assert len(df) == 2

    def test_column_names_are_lowercased(self, sample_sheet_factory):
        df = loadSampleSheet(sample_sheet_factory(['WCL']))
        assert all(c == c.lower() for c in df.columns)

    def test_required_columns_present(self, sample_sheet_factory):
        df = loadSampleSheet(sample_sheet_factory(['WCL']))
        for col in REQUIRED_COLUMNS:
            assert col in df.columns

    def test_raises_on_missing_column(self, sample_sheet_missing_col):
        with pytest.raises(ValueError, match='missing required column'):
            loadSampleSheet(sample_sheet_missing_col)

    def test_raises_on_duplicate_sample_ids(self, sample_sheet_duplicate_ids):
        with pytest.raises(ValueError, match='duplicate sample_id'):
            loadSampleSheet(sample_sheet_duplicate_ids)

    def test_raises_on_nonexistent_file(self, tmp_path):
        with pytest.raises(ValueError):
            loadSampleSheet(tmp_path / 'does_not_exist.tsv')

    def test_loads_csv_as_well_as_tsv(self, tmp_path):
        content = 'sample_id,raw_file,treatment,fraction,replicate\nS1,file.mzML,CTRL,WCL,1\n'
        p = tmp_path / 'sheet.csv'
        p.write_text(content)
        df = loadSampleSheet(p)
        assert len(df) == 1

    def test_optional_batch_column_allowed(self, sample_sheet_factory):
        df = loadSampleSheet(sample_sheet_factory(['WCL']))
        assert 'batch' in df.columns   # present in fixture, should not cause error

    def test_strips_whitespace_from_column_names(self, tmp_path):
        content = ' sample_id \t raw_file \t treatment \t fraction \t replicate \nS1\tf.mzML\tCTRL\tWCL\t1\n'
        p = tmp_path / 'spaced.tsv'
        p.write_text(content)
        df = loadSampleSheet(p)
        assert 'sample_id' in df.columns


# -- Define tests for filtering samples by treatment
class TestGetSamplesByTreatment:
    def test_filters_correctly(self, sample_sheet_factory):
        df = loadSampleSheet(sample_sheet_factory(['WCL']))
        result = getSamplesByTreatment(df, 'MOCK')
        assert len(result) == 1
        assert result.iloc[0]['sample_id'] == 'S1'

    def test_case_insensitive(self, sample_sheet_factory):
        df = loadSampleSheet(sample_sheet_factory(['WCL']))
        result = getSamplesByTreatment(df, 'mock')
        assert len(result) == 1

    def test_returns_empty_for_unknown_treatment(self, sample_sheet_factory):
        df = loadSampleSheet(sample_sheet_factory(['WCL']))
        result = getSamplesByTreatment(df, 'NONEXISTENT')
        assert len(result) == 0

    def test_returns_copy_not_view(self, sample_sheet_factory):
        df = loadSampleSheet(sample_sheet_factory(['WCL']))
        result = getSamplesByTreatment(df, 'MOCK')
        result['sample_id'] = 'MODIFIED'
        original = loadSampleSheet(sample_sheet_factory(['WCL']))
        assert original.iloc[0]['sample_id'] == 'S1'

# -- Define tests for filtering samples by fraction
class TestGetSamplesByFraction:
    def test_filters_correctly(self, sample_sheet_factory):
        df = loadSampleSheet(sample_sheet_factory(['WCL']))
        result = getSamplesByFraction(df, 'WCL')
        assert len(result) == 2
        assert result.iloc[0]['sample_id'] == 'S1'

    def test_case_insensitive(self, sample_sheet_factory):
        df = loadSampleSheet(sample_sheet_factory(['WCL']))
        result = getSamplesByFraction(df, 'wcl')
        assert len(result) == 2

    def test_returns_empty_for_unknown_treatment(self, sample_sheet_factory):
        df = loadSampleSheet(sample_sheet_factory(['WCL']))
        result = getSamplesByFraction(df, 'NONEXISTENT')
        assert len(result) == 0

    def test_returns_copy_not_view(self, sample_sheet_factory):
        df = loadSampleSheet(sample_sheet_factory(['WCL']))
        result = getSamplesByFraction(df, 'WCL')
        result['sample_id'] = 'MODIFIED'
        original = loadSampleSheet(sample_sheet_factory(['WCL']))
        assert original.iloc[0]['sample_id'] == 'S1'

# -- Define tests for creating file map
class TestGetRawFileMap:
    def test_maps_existing_files(self, sample_sheet_factory, tmp_path):
        df = loadSampleSheet(sample_sheet_factory(['WCL']))
        # Create the dummy mzML file in tmp_path so it is "found"
        (tmp_path / 'sample_mock_wcl_1.RAW').touch()
        (tmp_path / 'sample_treat_wcl_1.RAW').touch()
        file_map = getRawFileMap(df, tmp_path)
        assert 'S1' in file_map
        assert 'S2' in file_map

    def test_omits_missing_files(self, sample_sheet_factory, tmp_path):
        df = loadSampleSheet(sample_sheet_factory(['WCL']))
        # Do NOT create synthetic.mzML — file does not exist
        file_map = getRawFileMap(df, tmp_path)
        assert file_map == {}

    def test_returns_path_objects(self, sample_sheet_factory, tmp_path):
        df = loadSampleSheet(sample_sheet_factory(['WCL']))
        (tmp_path / 'sample_mock_wcl_1.RAW').touch()
        (tmp_path / 'sample_treat_wcl_1.RAW').touch()
        file_map = getRawFileMap(df, tmp_path)
        for v in file_map.values():
            assert isinstance(v, Path)
