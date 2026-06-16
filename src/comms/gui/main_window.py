'''
comMS experiment GUI: main window
'''

# -- Import external dependencies
from PySide6.QtCore import QSize
from PySide6.QtWidgets import QMainWindow, QTabWidget

# -- Import internal functions
from comms.gui.models.experiment_state import ExperimentState
from comms.gui.panels.experiment_header import ExperimentHeaderPanel
from comms.gui.panels.sample_panel import SamplePanel
from comms.gui.panels.config_panel import ConfigPanel
from comms.gui.panels.save_panel import SavePanel
from comms.gui.widgets.status_indicator import status_icon


# -- MainWindow: four numbered tabs with per-tab status icons
class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('comms experiment')
        self.resize(1100, 720)

        self.state = ExperimentState()
        self.header = ExperimentHeaderPanel()
        self.sample = SamplePanel(self.state)
        self.config = ConfigPanel()
        self.save = SavePanel(self.header, self.sample, self.config)

        self.tabs = QTabWidget()
        self.tabs.setIconSize(QSize(14, 14))
        self._exp_index = self.tabs.addTab(self.header, 'Experiment Information')
        self._sample_index = self.tabs.addTab(self.sample, 'Sample Information')
        self._config_index = self.tabs.addTab(self.config, 'Analysis Information')
        self._save_index = self.tabs.addTab(self.save, 'Save Experiment')
        self.setCentralWidget(self.tabs)

        # tab icons follow each panel's tracker
        self.header.tracker.statusChanged.connect(
            lambda s: self.tabs.setTabIcon(self._exp_index, status_icon(s)))
        self.sample.tracker.statusChanged.connect(
            lambda s: self.tabs.setTabIcon(self._sample_index, status_icon(s)))
        self.config.tracker.statusChanged.connect(
            lambda s: self.tabs.setTabIcon(self._config_index, status_icon(s)))

        # keep the save summary current
        self.header.changed.connect(self.save.refresh)
        self.sample.contentChanged.connect(self.save.refresh)
        self.config.changed.connect(self.save.refresh)
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # paint the initial (pristine) icons
        self.tabs.setTabIcon(self._exp_index, status_icon(self.header.tracker.status))
        self.tabs.setTabIcon(self._sample_index, status_icon(self.sample.tracker.status))
        self.tabs.setTabIcon(self._config_index, status_icon(self.config.tracker.status))
        self.save.refresh()

    def _on_tab_changed(self, index: int) -> None:
        if index == self._save_index:
            self.save.refresh()