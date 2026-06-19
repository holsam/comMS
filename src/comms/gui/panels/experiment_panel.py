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
        # Add output directory field and create layout
        self._dir = QLineEdit()
        self._dir.setMinimumWidth(360)
        self._dir.setPlaceholderText('directory to save experiment to')
        self._dir.textChanged.connect(self.changed)
        browse = QPushButton('Select directory')
        browse.clicked.connect(self._browse)
        dir_row = QWidget()
        dir_layout = QHBoxLayout(dir_row)
        dir_layout.setContentsMargins(0, 0, 0, 0)
        dir_layout.addWidget(self._dir)
        dir_layout.addWidget(browse)
        # Add database field and create layout
        self._database = QLineEdit()
        self._database.setMinimumWidth(360)
        self._database.setPlaceholderText('proteome FASTA file database')
        self._database.textChanged.connect(self.changed)
        database_browse = QPushButton('Select database')
        database_browse.clicked.connect(self._browse_database)
        database_row = QWidget()
        database_layout = QHBoxLayout(database_row)
        database_layout.setContentsMargins(0, 0, 0, 0)
        database_layout.addWidget(self._database)
        database_layout.addWidget(database_browse)
        # Add bin directory field and create layout
        self._bin = QLineEdit()
        self._bin.setMinimumWidth(360)
        self._bin.setPlaceholderText('optional: directory containing Crux / ThermoRawFileParser')
        self._bin.textChanged.connect(self.changed)
        bin_browse = QPushButton('Select directory')
        bin_browse.clicked.connect(self._browse_bin)
        bin_row = QWidget()
        bin_layout = QHBoxLayout(bin_row)
        bin_layout.setContentsMargins(0, 0, 0, 0)
        bin_layout.addWidget(self._bin)
        bin_layout.addWidget(bin_browse)
        # Add organism prefix field and create layout
        self._organism_prefix = QLineEdit()
        self._organism_prefix.setMinimumWidth(360)
        self._organism_prefix.setPlaceholderText('optional: organism prefix for report')
        self._organism_prefix.textChanged.connect(self.changed)
        # Add fields
        form.addRow('Experiment', self._name)
        form.addRow('Save to', dir_row)
        form.addRow('FASTA database', database_row)
        form.addRow('Binary directory', bin_row)
        form.addRow('Primary organism prefix', self._organism_prefix)
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
        signature = (self.experiment_name(), str(self.base_dir()), str(self.bin_dir()))
        self.tracker.mark_changed(signature, self.is_valid())

    def _browse(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, 'Select experiment directory')
        if chosen:
            self._dir.setText(chosen)

    def _browse_bin(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, 'Select bin directory')
        if chosen:
            self._bin.setText(chosen)

    def _browse_database(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, 'Select FASTA database', '', 'FASTA file (*.fa, *.fasta);;All files (*)')
        if path:
            self._state.sample_model.add_files(path)

    def experiment_name(self) -> str:
        return self._name.text().strip()
    
    def base_dir(self) -> Path | None:
        text = self._dir.text().strip()
        return Path(text) if text else None
    
    def output_dir(self) -> Path | None:
        base = self.base_dir()
        return base / 'comms' if base else None

    def bin_dir(self) -> Path | None:
        text = self._bin.text().strip()
        return Path(text) if text else None

    def database_path(self) -> Path | None:
        text = self._database.text().strip()
        return Path(text) if text else None

    def organism_prefix(self) -> str:
        return self._organism_prefix.text().strip()

    # sync_tracker: refresh the tracker from current content (used before unified save)
    def sync_tracker(self) -> None:
        self._on_changed()

    # -- write_metadata: write experiment.toml, recording name, timestamp and output paths
    def write_metadata(self, out_dir: Path, files: dict | None = None, analysis=None) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / 'experiment.toml'
        meta = {
            'experiment': {
                'name': self.experiment_name(),
                'updated': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            }
        }
        bin_dir = self.bin_dir()
        if bin_dir:
            meta['experiment']['bin_dir'] = str(bin_dir)
        if files:
            meta['files'] = {key: [str(v) for v in value] if isinstance(value, (list, tuple)) else str(value) for key, value in files.items()}
        if analysis:
            meta['experiment']['analysis'] = analysis
        with path.open('wb') as f:
            tomli_w.dump(meta, f)
        return path

    def is_valid(self) -> bool:
        return bool(self.experiment_name()) and self.base_dir() is not None and self.database_path() is not None