'''
comMS experiment GUI: command-readiness panel
'''

# -- Import external dependencies
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QGroupBox, QLabel,
)

# -- Import internal functions
from comms.utils.readiness import COMMANDS, missing_requirements
from comms.gui.widgets.status_indicator import StatusIndicator
from comms.gui.status import PanelStatus


# -- Define class CommandReadinessPanel to show, per command, whether the experiment can run it
class CommandReadinessPanel(QWidget):
    '''
    A read-only summary: one row per comMS command with a status glyph and the inputs still missing; recomputed via refresh() when a source panel changes
    '''
    def __init__(self, experiment, sample, config, parent=None):
        super().__init__(parent)
        self._experiment = experiment
        self._sample = sample
        self._config = config

        layout = QVBoxLayout(self)
        box = QGroupBox('Command readiness')
        grid = QGridLayout(box)
        grid.setColumnStretch(2, 1)

        self._indicators: dict[str, StatusIndicator] = {}
        self._details: dict[str, QLabel] = {}
        for row, command in enumerate(COMMANDS):
            indicator = StatusIndicator()
            name = QLabel(command)
            detail = QLabel()
            detail.setStyleSheet('color: gray;')
            grid.addWidget(indicator, row, 0, Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(name, row, 1)
            grid.addWidget(detail, row, 2)
            self._indicators[command] = indicator
            self._details[command] = detail

        layout.addWidget(box)
        layout.addStretch(1)
        self.refresh()

    # -- _state: gather the booleans the readiness model needs from the source panels
    def _state(self) -> dict:
        return dict(
            has_data=len(self._sample.data_files()) > 0,
            has_database=bool(self._experiment.database_path()),
            has_sample_sheet=self._sample.is_complete(),
            has_organism_prefix=bool(self._config.organism_prefix()),
            multispecies=self._config.analysis_mode() == 'multi',
            has_organism_tags=self._config.has_organism_patterns(),
        )

    # -- refresh: recompute readiness and repaint each row
    def refresh(self) -> None:
        missing = missing_requirements(**self._state())
        for command in COMMANDS:
            gaps = list(dict.fromkeys(missing[command]))   # dedupe, keep order (pipeline repeats)
            ready = not gaps
            self._indicators[command].setStatus(
                PanelStatus.COMPLETE if ready else PanelStatus.UNEDITED
            )
            text = 'ready' if ready else 'needs ' + ', '.join(gaps)
            self._details[command].setText(text)
            tooltip = 'Ready to run' if ready else 'Missing: ' + ', '.join(gaps)
            self._indicators[command].setToolTip(tooltip)
            self._details[command].setToolTip(tooltip)