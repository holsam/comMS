'''
Unit tests for src/comms/gui/panels/*
'''

# -- Import external dependencies
import pytest
import tomllib
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidgetItem

# -- Import functions under test
from comms.commands.config import MET_OX_MOD
from comms.gui.status import PanelStatus
from comms.gui.models.experiment_state import ExperimentState
from comms.gui.models.sample_table import COL_TREATMENT, COL_FRACTION
from comms.gui.panels.config_panel import ConfigPanel
from comms.gui.panels.experiment_panel import ExperimentPanel
from comms.gui.panels.sample_panel import SamplePanel
from comms.gui.panels.save_panel import SavePanel

pytestmark = pytest.mark.usefixtures('qapp')

# -- Define tests for config_panel
class TestConfigPanel:
    # Analysis type tests
    def test_defaults_to_single_species(self):
        assert ConfigPanel()._is_multispecies() is False

    def test_organism_box_disabled_for_single_species(self):
        assert ConfigPanel()._org_box.isEnabled() is False

    def test_organism_box_enabled_for_multispecies(self):
        p = ConfigPanel()
        p._analysis.setCurrentIndex(1)
        assert p._org_box.isEnabled() is True
    
    # Completeness tests
    def test_single_species_complete_without_organisms(self):
        assert ConfigPanel().is_complete() is True

    def test_multispecies_incomplete_without_organisms(self):
        p = ConfigPanel()
        p._analysis.setCurrentIndex(1)
        assert p.is_complete() is False

    def test_multispecies_incomplete_with_half_filled_row(self):
        p = ConfigPanel()
        p._analysis.setCurrentIndex(1)
        p._add_org_row()
        p._org_table.setItem(0, 0, QTableWidgetItem('EUK'))
        assert p.is_complete() is False

    def test_multispecies_complete_with_full_row(self):
        p = ConfigPanel()
        p._analysis.setCurrentIndex(1)
        p._add_org_row()
        p._org_table.setItem(0, 0, QTableWidgetItem('EUK'))
        p._org_table.setItem(0, 1, QTableWidgetItem('TESTEUK'))
        assert p.is_complete() is True
    
    # Config build tests
    def test_returns_dict_with_search_section(self):
        cfg = ConfigPanel()._build_config()
        assert isinstance(cfg, dict)
        assert 'search' in cfg

    def test_default_includes_met_oxidation(self):
        assert MET_OX_MOD in ConfigPanel()._build_config()['index']['mods_spec']

    def test_custom_mod_written_to_index(self):
        panel = ConfigPanel()
        panel._custom.setText('1K+28.0313')
        assert '1K+28.0313' in panel._build_config()['index']['custom_mods']

    def test_single_species_writes_empty_organism_section(self):
        assert ConfigPanel()._build_config()['organism'] == {}

    def test_multispecies_writes_organism_patterns(self):
        p = ConfigPanel()
        p._analysis.setCurrentIndex(1)
        p._add_org_row()
        p._org_table.setItem(0, 0, QTableWidgetItem('EUK'))
        p._org_table.setItem(0, 1, QTableWidgetItem('TESTEUK'))
        assert p._build_config()['organism'] == {'EUK': 'TESTEUK'}

    # State tests
    def test_changed_signal_and_tracker_update(self):
        p = ConfigPanel()
        seen = []
        p.changed.connect(lambda: seen.append(True))
        p._phos.setChecked(True)
        assert seen
        assert p.tracker.status is PanelStatus.COMPLETE

    def test_summary_reports_single_species(self):
        assert 'single species' in ConfigPanel().summary()

# -- Define tests for experiment_panel
class TestExperimentPanel:
    def test_experiment_name_strips_whitespace(self):
        p = ExperimentPanel()
        p._name.setText('  exp  ')
        assert p.experiment_name() == 'exp'

    def test_base_dir_none_when_empty(self):
        assert ExperimentPanel().base_dir() is None

    def test_output_dir_appends_comms(self, tmp_path):
        p = ExperimentPanel()
        p._dir.setText(str(tmp_path))
        assert p.output_dir() == tmp_path / 'comms'

    def test_bin_dir_optional_and_written(self, tmp_path):
        p = ExperimentPanel()
        p._name.setText('exp')
        p._dir.setText(str(tmp_path))
        p._bin.setText(str(tmp_path / 'bin'))
        assert p.is_valid() is True   # bin dir does not affect validity
        meta_path = p.write_metadata(tmp_path / 'comms')
        import tomllib
        with meta_path.open('rb') as f:
            meta = tomllib.load(f)
        assert meta['experiment']['bin_dir'] == str(tmp_path / 'bin')

    def test_is_valid_requires_name_and_dir(self, tmp_path):
        p = ExperimentPanel()
        assert p.is_valid() is False
        p._name.setText('exp')
        assert p.is_valid() is False
        p._dir.setText(str(tmp_path))
        assert p.is_valid() is True

    def test_tracker_incomplete_until_valid(self, tmp_path):
        p = ExperimentPanel()
        p._name.setText('exp')
        assert p.tracker.status is PanelStatus.INCOMPLETE
        p._dir.setText(str(tmp_path))
        assert p.tracker.status is PanelStatus.COMPLETE

# -- Helper: bring a sample panel's state to completeness
def _complete_sample(state):
    state.add_treatment('MOCK')
    state.add_fraction('WCL')
    model = state.sample_model
    if not model.rows():
        model.add_files(['/data/sample_a.RAW'])
    for r in range(len(model.rows())):
        model.setData(model.index(r, COL_TREATMENT), 'MOCK', Qt.ItemDataRole.EditRole)
        model.setData(model.index(r, COL_FRACTION), 'WCL', Qt.ItemDataRole.EditRole)

class TestSamplePanel:
    def test_is_complete_proxies_model(self):
        state = ExperimentState()
        panel = SamplePanel(state)
        assert panel.is_complete() is False
        _complete_sample(state)
        assert panel.is_complete() is True

    def test_content_changed_re_emitted(self):
        state = ExperimentState()
        panel = SamplePanel(state)
        seen = []
        panel.contentChanged.connect(lambda: seen.append(True))
        state.sample_model.add_files(['/data/a.RAW'])
        assert seen

    def test_tracker_incomplete_then_complete(self):
        state = ExperimentState()
        panel = SamplePanel(state)
        state.sample_model.add_files(['/data/a.RAW'])
        assert panel.tracker.status is PanelStatus.INCOMPLETE
        _complete_sample(state)
        assert panel.tracker.status is PanelStatus.COMPLETE

    def test_write_creates_sample_sheet(self, tmp_path):
        state = ExperimentState()
        panel = SamplePanel(state)
        _complete_sample(state)
        path = panel.write(tmp_path)
        assert path == tmp_path / 'sample_sheet.tsv'
        assert 'sample_a' in path.read_text()

class TestSavePanel:
    def _build(self, tmp_path):
        header = ExperimentPanel()
        header._name.setText('exp')
        header._dir.setText(str(tmp_path))
        state = ExperimentState()
        sample = SamplePanel(state)
        _complete_sample(state)
        config = ConfigPanel()    # single species: complete by default
        return header, sample, config, SavePanel(header, sample, config)

    def test_save_button_disabled_when_incomplete(self):
        header = ExperimentPanel()
        sample = SamplePanel(ExperimentState())
        config = ConfigPanel()
        save = SavePanel(header, sample, config)
        save.refresh()
        assert save.save_button.isEnabled() is False

    def test_save_button_enabled_when_all_complete(self, tmp_path):
        *_, save = self._build(tmp_path)
        save.refresh()
        assert save.save_button.isEnabled() is True

    def test_save_all_writes_three_files(self, tmp_path):
        *_, save = self._build(tmp_path)
        with patch('comms.gui.panels.save_panel.QMessageBox.information'):
            save._save_all()
        out = tmp_path / 'comms'
        assert (out / 'sample_sheet.tsv').exists()
        assert (out / 'config.toml').exists()
        assert (out / 'experiment.toml').exists()

    def test_save_all_records_paths_in_metadata(self, tmp_path):
        *_, save = self._build(tmp_path)
        with patch('comms.gui.panels.save_panel.QMessageBox.information'):
            save._save_all()
        with (tmp_path / 'comms' / 'experiment.toml').open('rb') as f:
            meta = tomllib.load(f)
        assert 'sample_sheet' in meta['files']
        assert 'config' in meta['files']

    def test_save_all_marks_trackers_saved(self, tmp_path):
        header, sample, config, save = self._build(tmp_path)
        with patch('comms.gui.panels.save_panel.QMessageBox.information'):
            save._save_all()
        assert header.tracker.status is PanelStatus.SAVED
        assert sample.tracker.status is PanelStatus.SAVED
        assert config.tracker.status is PanelStatus.SAVED

    def test_saved_signal_emitted(self, tmp_path):
        *_, save = self._build(tmp_path)
        seen = []
        save.saved.connect(lambda: seen.append(True))
        with patch('comms.gui.panels.save_panel.QMessageBox.information'):
            save._save_all()
        assert seen

    def test_records_name(self, tmp_path):
        p = ExperimentPanel()
        p._name.setText('exp')
        path = p.write_metadata(tmp_path)
        with path.open('rb') as f:
            meta = tomllib.load(f)
        assert meta['experiment']['name'] == 'exp'