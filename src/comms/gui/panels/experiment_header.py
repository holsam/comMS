'''
comMS experiment GUI: header panel
'''

# -- Import external dependencies
import tomli_w
from datetime import datetime, timezone
from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QHBoxLayout, QPushButton, QFileDialog,
)

# Import PanelStateTracker class
from comms.gui.status import PanelStateTracker

# -- Define class ExperimentHeaderPanel to collect experiment name and base output directory
class ExperimentHeaderPanel(QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        form = QFormLayout(self)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        # Add experiment name field
        self._name = QLineEdit()
        self._name.setMinimumWidth(360)
        self._name.setPlaceholderText('name for experiment')
        self._name.textChanged.connect(self.changed)
        # Add output directory field
        self._dir = QLineEdit()
        self._dir.setMinimumWidth(360)
        self._dir.setPlaceholderText('directory to save experiment to')
        self._dir.textChanged.connect(self.changed)
        browse = QPushButton('Select Directory')
        browse.clicked.connect(self._browse)
        # Create output directory field layout
        dir_row = QWidget()
        dir_layout = QHBoxLayout(dir_row)
        dir_layout.setContentsMargins(0, 0, 0, 0)
        dir_layout.addWidget(self._dir)
        dir_layout.addWidget(browse)
        # Add fields
        form.addRow('Experiment', self._name)
        form.addRow('Save Directory', dir_row)
        # Add status tracker
        self.tracker = PanelStateTracker(self)
        self.changed.connect(self._on_changed)

    def _on_changed(self) -> None:
        signature = (self.experiment_name(), str(self.base_dir()))
        self.tracker.mark_changed(signature, self.is_valid())

    def _browse(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, 'Select experiment output directory')
        if chosen:
            self._dir.setText(chosen)

    def experiment_name(self) -> str:
        return self._name.text().strip()
    
    def base_dir(self) -> Path | None:
        text = self._dir.text().strip()
        return Path(text) if text else None
    
    def output_dir(self) -> Path | None:
        base = self.base_dir()
        return base / 'comms' if base else None

    def write_metadata(self) -> Path | None:
        out_dir = self.output_dir()
        if out_dir is None:
            return None
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / 'experiment.toml'
        meta = {
            'experiment': {
                'name': self.experiment_name(),
                'updated': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            }
        }
        with path.open('wb') as f:
            tomli_w.dump(meta, f)

    def is_valid(self) -> bool:
        return bool(self.experiment_name()) and self.base_dir() is not None