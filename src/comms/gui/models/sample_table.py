'''
comMS experiment GUI — sample sheet table model
'''

# -- Import external dependencies
from dataclasses import dataclass
from pathlib import Path
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal

# Import SampleRow dataclass and render_sample_sheet function
from comms.utils.sheet import (
    SampleRow, COLUMNS, HEADER_LABELS as _HEADER_LABELS, render_sample_sheet, COL_SAMPLE_ID, COL_RAW, COL_TREATMENT, COL_FRACTION, COL_REPLICATE, COL_BATCH
)

# Define editable columns
_EDITABLE = {COL_SAMPLE_ID, COL_TREATMENT, COL_FRACTION, COL_REPLICATE, COL_BATCH}

# -- Define class SampleTableModel to hold an editable table model backed by a list of SampleRow
class SampleTableModel(QAbstractTableModel):
    contentChanged = Signal()

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self._state = state
        self._rows: list[SampleRow] = []
        state.groupsChanged.connect(self._on_groups_changed)

    # -- Qt model interface --
    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(COLUMNS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            name = COLUMNS[section]
            return _HEADER_LABELS.get(name, name)
        return section + 1

    def flags(self, index):
        base = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if index.column() in _EDITABLE:
            return base | Qt.ItemFlag.ItemIsEditable
        return base

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role not in (
            Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole
        ):
            return None
        row = self._rows[index.row()]
        value = (
            row.sample_id, row.raw_file, row.treatment,
            row.fraction, row.replicate, row.batch,
        )[index.column()]
        return '' if value is None else str(value)

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        row = self._rows[index.row()]
        col = index.column()
        text = str(value).strip()
        if col == COL_SAMPLE_ID:
            row.sample_id = text
        elif col == COL_TREATMENT:
            row.treatment = text
        elif col == COL_FRACTION:
            row.fraction = text
        elif col == COL_REPLICATE:
            row.replicate = self._coerce_replicate(text)
            row.replicate_overridden = text != ''
        elif col == COL_BATCH:
            row.batch = text
        else:
            return False
        self.dataChanged.emit(index, index)
        if col in (COL_TREATMENT, COL_FRACTION):
            self._renumber_replicates()
        self.contentChanged.emit()
        return True

    # -- public helpers --
    def set_rows(self, rows: list[SampleRow]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()
        self._renumber_replicates()
        self.contentChanged.emit()

    # -- add_files: append a SampleRow per path, skipping files already present
    def add_files(self, paths) -> None:
        existing = {r.raw_file for r in self._rows}
        new = [Path(p) for p in paths if Path(p).name not in existing]
        if not new:
            return
        start = len(self._rows)
        self.beginInsertRows(QModelIndex(), start, start + len(new) - 1)
        for p in new:
            self._rows.append(SampleRow(sample_id=p.stem, raw_file=p.name, source_path=str(p)))
        self.endInsertRows()
        self._renumber_replicates()
        self.contentChanged.emit()

    # -- remove_rows: delete the given row indices
    def remove_rows(self, rows) -> None:
        for i in sorted(set(rows), reverse=True):
            if 0 <= i < len(self._rows):
                self.beginRemoveRows(QModelIndex(), i, i)
                del self._rows[i]
                self.endRemoveRows()
        self._renumber_replicates()
        self.contentChanged.emit()

    def rows(self) -> list[SampleRow]:
        return list(self._rows)

    # -- is_complete: every row has the required fields and sample_ids are unique
    def is_complete(self) -> bool:
        if not self._rows:
            return False
        ids = [r.sample_id for r in self._rows]
        if any(not v for v in ids) or len(set(ids)) != len(ids):
            return False
        return all(r.treatment and r.fraction and r.replicate is not None for r in self._rows)

    def signature(self):
        return tuple(
            (r.sample_id, r.raw_file, r.treatment, r.fraction, r.replicate, r.batch)
            for r in self._rows
        )

    # -- internal --
    @staticmethod
    def _coerce_replicate(text: str):
        if text == '':
            return None
        try:
            return int(text)
        except ValueError:
            return None

    # -- _renumber_replicates: assign 1..n per (treatment, fraction), skipping overrides
    def _renumber_replicates(self) -> None:
        counters: dict[tuple[str, str], int] = {}
        for r in self._rows:
            if not r.treatment or not r.fraction:
                continue
            key = (r.treatment, r.fraction)
            counters.setdefault(key, 0)
            if r.replicate_overridden:
                counters[key] = max(counters[key], r.replicate or 0)
            else:
                counters[key] += 1
                r.replicate = counters[key]
        if self._rows:
            top = self.index(0, COL_REPLICATE)
            bottom = self.index(self.rowCount() - 1, COL_REPLICATE)
            self.dataChanged.emit(top, bottom)

    # -- _on_groups_changed: clear selections that no longer exist, then renumber
    def _on_groups_changed(self) -> None:
        treatments = set(self._state.treatments)
        fractions = set(self._state.fractions)
        self.beginResetModel()
        for r in self._rows:
            if r.treatment and r.treatment not in treatments:
                r.treatment = ''
            if r.fraction and r.fraction not in fractions:
                r.fraction = ''
        self._renumber_replicates()
        self.endResetModel()
        self.contentChanged.emit()