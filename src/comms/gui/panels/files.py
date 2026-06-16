'''
comMS experiment GUI: files subpanel (to import files and assign metadata)
'''

# -- Import external dependencies
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableView, QFileDialog, QHeaderView, QAbstractItemView,
)

# -- Import internal functions
from comms.gui.models.experiment_state import ExperimentState
from comms.gui.models.sample_table import SampleRow, COL_TREATMENT, COL_FRACTION
from comms.gui.widgets.combo_delegate import GroupComboDelegate

# -- Define accepted input suffixes (matches the sample sheet raw_file column)
_RAW_SUFFIXES = {'.raw', '.mzml'}

# -- Define class FilesSubPanel to import RAW/mzML filenames and edit per-sample metadata
class FilesSubPanel(QWidget):
    def __init__(self, state: ExperimentState, parent=None):
        super().__init__(parent)
        self._state = state
        layout = QVBoxLayout(self)

        controls = QHBoxLayout()
        select_btn = QPushButton('Select data directory')
        select_btn.clicked.connect(self._select_directory)
        self._path_label = QLabel('No directory selected')
        controls.addWidget(select_btn)
        controls.addWidget(self._path_label, 1)
        layout.addLayout(controls)

        self._table = QTableView()
        self._table.setModel(state.sample_model)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.SelectedClicked | QAbstractItemView.EditTrigger.CurrentChanged)
        self._table.setItemDelegateForColumn(
            COL_TREATMENT, GroupComboDelegate(lambda: state.treatments, self._table))
        self._table.setItemDelegateForColumn(
            COL_FRACTION, GroupComboDelegate(lambda: state.fractions, self._table))
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table)

    def _select_directory(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, 'Select directory containing data files')
        if not chosen:
            return
        directory = Path(chosen)
        files = sorted(
            p for p in directory.iterdir()
            if p.is_file() and p.suffix.lower() in _RAW_SUFFIXES
        )
        rows = [SampleRow(sample_id=p.stem, raw_file=p.name) for p in files]
        self._state.sample_model.set_rows(rows)
        self._path_label.setText(f'{directory}  ({len(rows)} file(s))')