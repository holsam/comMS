'''
comMS experiment GUI: main window
'''

# -- Import external dependencies
from pathlib import Path
from PySide6.QtCore import QSize
from PySide6.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget

# -- Import internal functions
from comms.gui.models.experiment_state import ExperimentState
from comms.gui.panels.experiment_panel import ExperimentPanel
from comms.gui.panels.readiness_panel import CommandReadinessPanel
from comms.gui.panels.sample_panel import SamplePanel
from comms.gui.panels.config_panel import ConfigPanel
from comms.gui.panels.save_panel import SavePanel
from comms.gui.widgets.status_indicator import status_icon
from comms.utils.log import logMsg

# -- MainWindow: four numbered tabs with per-tab status icons
class MainWindow(QMainWindow):
    def __init__(self, experiment_dir: Path | None = None, parent=None):
        super().__init__(parent)
        self._log = logMsg('experiment')
        self.setWindowTitle('comms experiment setup')
        self.resize(1100, 720)

        self.state = ExperimentState()
        self.experiment = ExperimentPanel()
        self.sample = SamplePanel(self.state)
        self.config = ConfigPanel()
        self.save = SavePanel(self.experiment, self.sample, self.config)
        self.readiness = CommandReadinessPanel(self.experiment, self.sample, self.config)
        
        review_tab = QWidget()
        review_layout = QVBoxLayout(review_tab)
        review_layout.addWidget(self.experiment)
        review_layout.addWidget(self.readiness)
        review_layout.addWidget(self.save)

        self.tabs = QTabWidget()
        self.tabs.setIconSize(QSize(14, 14))
        self._sample_index = self.tabs.addTab(self.sample, 'Sample Information')
        self._config_index = self.tabs.addTab(self.config, 'Analysis Information')
        self._review_index = self.tabs.addTab(review_tab, 'Review Experiment')
        self.setCentralWidget(self.tabs)

        # tab icons follow each panel's tracker
        self.sample.tracker.statusChanged.connect(
            lambda s: self.tabs.setTabIcon(self._sample_index, status_icon(s)))
        self.config.tracker.statusChanged.connect(
            lambda s: self.tabs.setTabIcon(self._config_index, status_icon(s)))
        self.experiment.tracker.statusChanged.connect(
            lambda s: self.tabs.setTabIcon(self._review_index, status_icon(s)))

        # keep the save summary current
        self.sample.contentChanged.connect(self.save.refresh)
        self.config.changed.connect(self.save.refresh)
        self.experiment.changed.connect(self.save.refresh)
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # wire the command readiness panel
        self.sample.contentChanged.connect(self.readiness.refresh)
        self.config.changed.connect(self.readiness.refresh)
        self.experiment.changed.connect(self.readiness.refresh)

        # paint the initial (unedited) icons
        self.tabs.setTabIcon(self._sample_index, status_icon(self.sample.tracker.status))
        self.tabs.setTabIcon(self._config_index, status_icon(self.config.tracker.status))
        self.tabs.setTabIcon(self._review_index, status_icon(self.experiment.tracker.status))
        self.save.refresh()
        
        # if a directory provided, call _load_existing
        if experiment_dir is not None:
            self._load_existing(experiment_dir)

    def _on_tab_changed(self, index: int) -> None:
        if index == self._review_index:
            self.save.refresh()

    def _load_existing(self, experiment_dir: Path) -> None:
        from comms.commands.experiment import _existing_experiment
        existing = _existing_experiment(experiment_dir)
        if existing is None:
            # If no experiment actually saved to directory, only pre-fill save to field
            self.experiment._dir.setText(str(experiment_dir))
            return
        root, comms_dir, metadata, config, rows = existing
        self.experiment.load_from_metadata(root, metadata)
        report_meta = metadata.get('report', {})
        self.config.load_from_config(config, report_meta)
        treatments = sorted({r.treatment for r in rows if r.treatment})
        fractions = sorted({r.fraction for r in rows if r.fraction})
        data_files = metadata.get('files', {}).get('data', [])
        self.sample.load(rows, treatments, fractions, data_files=data_files)
        self._log.info(f'Loaded existing experiment from {comms_dir}')

    def closeEvent(self, event) -> None:
        self._log.info('Closed experiment setup GUI')
        super().closeEvent(event)