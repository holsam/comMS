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
from comms.gui.models.sample_table import COL_TREATMENT, COL_FRACTION
from comms.gui.widgets.combo_delegate import GroupComboDelegate

# -- Define the file picker filter
_FILE_FILTER = 'Mass spectrometry files (*.raw *.RAW *.mzML *.mzml);;All files (*)'

# -- Define class FilesSubPanel to add/remove sample files and edit per-sample metadata
class FilesSubPanel(QWidget):
    def __init__(self, state: ExperimentState, parent=None):
        super().__init__(parent)
        self._state = state
        layout = QVBoxLayout(self)

        controls = QHBoxLayout()
        self._count_label = QLabel('0 file(s)')
        controls.addWidget(self._count_label)
        controls.addStretch(1)
        add_btn = QPushButton('Add File')
        add_btn.clicked.connect(self._add_files)
        remove_btn = QPushButton('Remove Selected')
        remove_btn.clicked.connect(self._remove_selected)
        controls.addWidget(add_btn)
        controls.addWidget(remove_btn)
        layout.addLayout(controls)

        self._table = QTableView()
        self._table.setModel(state.sample_model)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.AllEditTriggers)
        self._table.setItemDelegateForColumn(
            COL_TREATMENT, GroupComboDelegate(lambda: state.treatments, self._table))
        self._table.setItemDelegateForColumn(
            COL_FRACTION, GroupComboDelegate(lambda: state.fractions, self._table))
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table)

        state.sample_model.contentChanged.connect(self._update_count)
        self._update_count()

    def _add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, 'Add mass spectrometry files', '', _FILE_FILTER)
        if paths:
            self._state.sample_model.add_files(paths)

    def _remove_selected(self) -> None:
        rows = sorted({i.row() for i in self._table.selectionModel().selectedRows()})
        if rows:
            self._state.sample_model.remove_rows(rows)

    def _update_count(self) -> None:
        n = len(self._state.sample_model.rows())
        self._count_label.setText(f'{n} file(s)')