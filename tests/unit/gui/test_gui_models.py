'''
Unit tests for src/comms/gui/models/*
'''

# -- Import external dependencies
import pytest
from PySide6.QtCore import Qt

# -- Import functions under test
from comms.gui.models.experiment_state import ExperimentState
from comms.gui.models.sample_table import (
    SampleRow, render_sample_sheet, COLUMNS,
    COL_SAMPLE_ID, COL_TREATMENT, COL_FRACTION, COL_REPLICATE, COL_BATCH,
)

pytestmark = pytest.mark.usefixtures('qapp')

class TestModelsExperimentState:
    def test_add_treatment_returns_true(self):
        s = ExperimentState()
        assert s.add_treatment('MOCK') is True
        assert s.treatments == ['MOCK']

    def test_duplicate_treatment_returns_false(self):
        s = ExperimentState()
        s.add_treatment('MOCK')
        assert s.add_treatment('MOCK') is False

    def test_empty_treatment_returns_false(self):
        assert ExperimentState().add_treatment('   ') is False

    def test_remove_treatment(self):
        s = ExperimentState()
        s.add_treatment('MOCK')
        s.remove_treatment('MOCK')
        assert s.treatments == []

    def test_add_fraction(self):
        s = ExperimentState()
        assert s.add_fraction('WCL') is True
        assert s.fractions == ['WCL']

    def test_groups_changed_emitted_on_add(self):
        s = ExperimentState()
        seen = []
        s.groupsChanged.connect(lambda: seen.append(True))
        s.add_treatment('MOCK')
        assert seen

    def test_treatments_returns_copy(self):
        s = ExperimentState()
        s.add_treatment('MOCK')
        s.treatments.append('X')
        assert s.treatments == ['MOCK']

# -- sample_helper helpers
def _model_with_files(stems):
    state = ExperimentState()
    state.add_treatment('MOCK')
    state.add_treatment('TREAT')
    state.add_fraction('WCL')
    model = state.sample_model
    model.add_files([f'/data/{stem}.RAW' for stem in stems])
    return state, model

def _set(model, row, col, value):
    model.setData(model.index(row, col), value, Qt.ItemDataRole.EditRole)

# -- Define tests for sample_table add_files
class TestSampleTableAddFiles:
    def test_appends_rows(self):
        model = ExperimentState().sample_model
        model.add_files(['/data/a.RAW', '/data/b.mzML'])
        assert len(model.rows()) == 2

    def test_sample_id_is_filename_stem(self):
        model = ExperimentState().sample_model
        model.add_files(['/data/sample_a.RAW'])
        assert model.rows()[0].sample_id == 'sample_a'

    def test_raw_file_is_filename(self):
        model = ExperimentState().sample_model
        model.add_files(['/data/sample_a.RAW'])
        assert model.rows()[0].raw_file == 'sample_a.RAW'

    def test_duplicate_files_skipped(self):
        model = ExperimentState().sample_model
        model.add_files(['/data/a.RAW'])
        model.add_files(['/data/a.RAW', '/data/b.RAW'])
        names = [r.raw_file for r in model.rows()]
        assert names.count('a.RAW') == 1
        assert 'b.RAW' in names

    def test_emits_content_changed(self):
        model = ExperimentState().sample_model
        seen = []
        model.contentChanged.connect(lambda: seen.append(True))
        model.add_files(['/data/a.RAW'])
        assert seen

# -- Define tests for sample_table remove_rows
class TestSampleTableRemoveRows:
    def test_deletes_single_row(self):
        model = ExperimentState().sample_model
        model.add_files(['/data/a.RAW', '/data/b.RAW', '/data/c.RAW'])
        model.remove_rows([1])
        assert [r.raw_file for r in model.rows()] == ['a.RAW', 'c.RAW']

    def test_deletes_multiple_rows(self):
        model = ExperimentState().sample_model
        model.add_files(['/data/a.RAW', '/data/b.RAW', '/data/c.RAW'])
        model.remove_rows([0, 2])
        assert [r.raw_file for r in model.rows()] == ['b.RAW']

# -- Define tests for sample_table is_complete
class TestSampleTableIsComplete:
    def test_empty_model_incomplete(self):
        assert ExperimentState().sample_model.is_complete() is False

    def test_incomplete_without_treatment(self):
        _, model = _model_with_files(['a'])
        _set(model, 0, COL_FRACTION, 'WCL')
        assert model.is_complete() is False

    def test_complete_when_all_fields_set(self):
        _, model = _model_with_files(['a'])
        _set(model, 0, COL_TREATMENT, 'MOCK')
        _set(model, 0, COL_FRACTION, 'WCL')
        assert model.is_complete() is True

    def test_duplicate_sample_ids_incomplete(self):
        _, model = _model_with_files(['a', 'b'])
        for r in (0, 1):
            _set(model, r, COL_TREATMENT, 'MOCK')
            _set(model, r, COL_FRACTION, 'WCL')
        _set(model, 1, COL_SAMPLE_ID, 'a')
        assert model.is_complete() is False

# -- Define tests for sample_table replicate auto-numbering
class TestTestSampleTableRenumberReplicates:
    def test_sequential_within_group(self):
        _, model = _model_with_files(['a', 'b'])
        for r in (0, 1):
            _set(model, r, COL_TREATMENT, 'MOCK')
            _set(model, r, COL_FRACTION, 'WCL')
        assert [row.replicate for row in model.rows()] == [1, 2]

    def test_separate_counters_per_group(self):
        _, model = _model_with_files(['a', 'b'])
        _set(model, 0, COL_TREATMENT, 'MOCK'); _set(model, 0, COL_FRACTION, 'WCL')
        _set(model, 1, COL_TREATMENT, 'TREAT'); _set(model, 1, COL_FRACTION, 'WCL')
        assert [row.replicate for row in model.rows()] == [1, 1]

    def test_manual_override_respected(self):
        _, model = _model_with_files(['a', 'b'])
        for r in (0, 1):
            _set(model, r, COL_TREATMENT, 'MOCK')
            _set(model, r, COL_FRACTION, 'WCL')
        _set(model, 0, COL_REPLICATE, '5')
        assert model.rows()[0].replicate == 5
        assert model.rows()[0].replicate_overridden is True

# -- Define tests for sample_table header labels
class TestTestSampleTableHeaderData:
    def test_batch_column_labelled_optional(self):
        model = ExperimentState().sample_model
        label = model.headerData(COL_BATCH, Qt.Orientation.Horizontal,
                                  Qt.ItemDataRole.DisplayRole)
        assert label == 'batch (optional)'

    def test_other_columns_use_canonical_names(self):
        model = ExperimentState().sample_model
        label = model.headerData(COL_TREATMENT, Qt.Orientation.Horizontal,
                                  Qt.ItemDataRole.DisplayRole)
        assert label == 'treatment'

# -- Define tests for sample_table render_sample_sheet
class TestTestSampleTableRenderSampleSheet:
    def test_header_uses_canonical_columns(self):
        assert render_sample_sheet([]).splitlines()[0] == '\t'.join(COLUMNS)

    def test_row_is_tab_joined(self):
        row = SampleRow('S1', 'a.RAW', 'MOCK', 'WCL', 1, 'A')
        assert render_sample_sheet([row]).splitlines()[1] == 'S1\ta.RAW\tMOCK\tWCL\t1\tA'

    def test_none_replicate_renders_empty(self):
        row = SampleRow('S1', 'a.RAW', 'MOCK', 'WCL', None, '')
        fields = render_sample_sheet([row]).splitlines()[1].split('\t')
        assert fields[4] == ''

    def test_trailing_newline(self):
        assert render_sample_sheet([]).endswith('\n')