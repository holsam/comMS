'''
Unit tests for src/comms/gui/panels/readiness_panel.py
'''
from unittest.mock import MagicMock, patch
import pytest

from comms.gui.panels.readiness_panel import CommandReadinessPanel


def _mock_panels(**overrides):
    experiment = MagicMock()
    experiment.bin_dir.return_value = overrides.get('bin_dir')
    experiment.database_path.return_value = overrides.get('database_path', '/db.fasta')
    sample = MagicMock()
    sample.data_files.return_value = overrides.get('data_files', ['/f1.RAW'])
    sample.is_complete.return_value = overrides.get('sample_complete', True)
    config = MagicMock()
    config.organism_prefix.return_value = overrides.get('organism_prefix', 'Mtrun')
    config.analysis_mode.return_value = overrides.get('analysis_mode', 'single')
    config.has_organism_patterns.return_value = overrides.get('has_organism_patterns', False)
    return experiment, sample, config


class TestReadinessPanel:
    def test_refresh_dependencies_probes_with_resolved_bin_dir(self, qapp, tmp_path):
        experiment, sample, config = _mock_panels(bin_dir=tmp_path)
        with patch('comms.gui.panels.readiness_panel.check_r_dependencies', return_value={'installed': [], 'missing': []}), \
             patch('comms.gui.panels.readiness_panel.repoBinDir', return_value=tmp_path) as mock_repo, \
             patch('comms.gui.panels.readiness_panel.probe_crux', return_value=None) as mock_crux, \
             patch('comms.gui.panels.readiness_panel.probe_trfp', return_value=None) as mock_trfp:
            panel = CommandReadinessPanel(experiment, sample, config)
            panel.refresh_dependencies()
        mock_repo.assert_called_with(experiment_bin_dir=tmp_path)
        mock_crux.assert_called_with(tmp_path)
        mock_trfp.assert_called_with(tmp_path)

    def test_bin_dir_change_is_reflected_on_next_refresh(self, qapp, tmp_path):
        '''Regression test: changing bin_dir and calling refresh_dependencies() must re-probe against the new path, not a stale one.'''
        experiment, sample, config = _mock_panels(bin_dir=tmp_path / 'old')
        with patch('comms.gui.panels.readiness_panel.check_r_dependencies', return_value={'installed': [], 'missing': []}), \
             patch('comms.gui.panels.readiness_panel.repoBinDir', side_effect=lambda experiment_bin_dir: experiment_bin_dir), \
             patch('comms.gui.panels.readiness_panel.probe_crux', return_value=None) as mock_crux, \
             patch('comms.gui.panels.readiness_panel.probe_trfp', return_value=None):
            panel = CommandReadinessPanel(experiment, sample, config)
            experiment.bin_dir.return_value = tmp_path / 'new'
            panel.refresh_dependencies()
        mock_crux.assert_called_with(tmp_path / 'new')

    def test_crux_and_trfp_found_states_reflected(self, qapp, tmp_path):
        experiment, sample, config = _mock_panels()
        with patch('comms.gui.panels.readiness_panel.check_r_dependencies', return_value={'installed': ['limma'], 'missing': []}), \
             patch('comms.gui.panels.readiness_panel.repoBinDir', return_value=tmp_path), \
             patch('comms.gui.panels.readiness_panel.probe_crux', return_value=tmp_path / 'crux'), \
             patch('comms.gui.panels.readiness_panel.probe_trfp', return_value=None):
            panel = CommandReadinessPanel(experiment, sample, config)
        assert panel._crux_found is True
        assert panel._trfp_found is False

    def test_tooltip_names_searched_directory(self, qapp, tmp_path):
        experiment, sample, config = _mock_panels()
        with patch('comms.gui.panels.readiness_panel.check_r_dependencies', return_value={'installed': [], 'missing': []}), \
             patch('comms.gui.panels.readiness_panel.repoBinDir', return_value=tmp_path), \
             patch('comms.gui.panels.readiness_panel.probe_crux', return_value=None), \
             patch('comms.gui.panels.readiness_panel.probe_trfp', return_value=None):
            panel = CommandReadinessPanel(experiment, sample, config)
        assert str(tmp_path) in panel._deps_label.toolTip()

    def test_missing_requirements_reflected_per_command(self, qapp, tmp_path):
        experiment, sample, config = _mock_panels(data_files=[])
        with patch('comms.gui.panels.readiness_panel.check_r_dependencies', return_value={'installed': [], 'missing': []}), \
             patch('comms.gui.panels.readiness_panel.repoBinDir', return_value=tmp_path), \
             patch('comms.gui.panels.readiness_panel.probe_crux', return_value=tmp_path / 'crux'), \
             patch('comms.gui.panels.readiness_panel.probe_trfp', return_value=tmp_path / 'trfp'):
            panel = CommandReadinessPanel(experiment, sample, config)
        assert 'data files' in panel._details['convert'].text()