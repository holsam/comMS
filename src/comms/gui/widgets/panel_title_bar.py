'''
comMS experiment GUI: panel title bar (label + status indicator)
'''

# -- Import external dependencies
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel

# -- Import internal functions
from comms.gui.status import PanelStatus
from comms.gui.widgets.status_indicator import StatusIndicator

# -- Define class PanelTitleBar to hold a left-aligned title with right-aligned status glyph
class PanelTitleBar(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 4)
        self._label = QLabel(title)
        self._label.setStyleSheet('font-weight: 600;')
        self._indicator = StatusIndicator()
        layout.addWidget(self._label)
        layout.addStretch(1)
        layout.addWidget(self._indicator)

    def set_status(self, status: PanelStatus) -> None:
        self._indicator.setStatus(status)