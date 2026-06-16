'''
comMS experiment GUI: header panel
'''

# -- Import external dependencies
import tomli_w
from datetime import datetime, timezone
from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QHBoxLayout, QPushButton, QFileDialog, QVBoxLayout,
)

# Import PanelStateTracker class
from comms.gui.status import PanelStateTracker

# -- Define class ExperimentPanel to collect experiment name and base output directory
class ExperimentPanel(QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # Add status tracker
        self.tracker = PanelStateTracker(self)
        form_widget = QWidget()
        form = QFormLayout(form_widget)
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
        browse = QPushButton('Select directory')
        browse.clicked.connect(self._browse)
        # Create output directory field layout
        dir_row = QWidget()
        dir_layout = QHBoxLayout(dir_row)
        dir_layout.setContentsMargins(0, 0, 0, 0)
        dir_layout.addWidget(self._dir)
        dir_layout.addWidget(browse)
        # Add fields
        form.addRow('Experiment', self._name)
        form.addRow('Save to', dir_row)
        # Organise layout
        centre_row = QHBoxLayout()
        centre_row.addStretch(1)
        centre_row.addWidget(form_widget)
        centre_row.addStretch(1)
        outer = QVBoxLayout(self)
        outer.addStretch(1)
        outer.addLayout(centre_row)
        outer.addStretch(1)
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
    
    # sync_tracker: refresh the tracker from current content (used before unified save)
    def sync_tracker(self) -> None:
        self._on_changed()

    # -- write_metadata: write experiment.toml, recording name, timestamp and output paths
    def write_metadata(self, out_dir: Path, files: dict | None = None) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / 'experiment.toml'
        meta = {
            'experiment': {
                'name': self.experiment_name(),
                'updated': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            }
        }
        if files:
            meta['files'] = {key: str(value) for key, value in files.items()}
        with path.open('wb') as f:
            tomli_w.dump(meta, f)
        return path

    def is_valid(self) -> bool:
        return bool(self.experiment_name()) and self.base_dir() is not None