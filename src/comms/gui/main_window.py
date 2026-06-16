'''
comMS experiment GUI: main window
'''

# -- Import external dependencies
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QSplitter

# -- Import internal functions
from comms.gui.models.experiment_state import ExperimentState
from comms.gui.panels.experiment_header import ExperimentHeaderPanel
from comms.gui.panels.sample_panel import SamplePanel
from comms.gui.panels.config_panel import ConfigPanel


# -- MainWindow: header plus the two main panels in a horizontal splitter
class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('comMS')
        self.resize(1100, 720)

        central = QWidget()
        layout = QVBoxLayout(central)

        self.header = ExperimentHeaderPanel()
        layout.addWidget(self.header)

        self.state = ExperimentState()
        self.sample_panel = SamplePanel(self.state, self.header)
        self.config_panel = ConfigPanel(self.header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.sample_panel)
        splitter.addWidget(self.config_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)

        self.setCentralWidget(central)