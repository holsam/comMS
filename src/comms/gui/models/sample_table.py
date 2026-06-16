'''
comMS experiment GUI — sample sheet table model
'''

# -- Import external dependencies
from dataclasses import dataclass
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal

# -- Define dataclass SampleRow to hold a sample sheet row
@dataclass
class SampleRow:
    sample_id: str
    raw_file: str
    treatment: str = ''
    fraction: str = ''
    replicate: int | None = None
    batch: str = ''
    replicate_overridden: bool = False

# -- Define column layout to mirror comMS sample sheet schema
COLUMNS = ['sample_id', 'raw_file', 'treatment', 'fraction', 'replicate', 'batch']
COL_SAMPLE_ID, COL_RAW, COL_TREATMENT, COL_FRACTION, COL_REPLICATE, COL_BATCH = range(6)
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
            return COLUMNS[section]
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

# -- render_sample_sheet: build the TSV text for a list of SampleRow
def render_sample_sheet(rows) -> str:
    lines = ['\t'.join(COLUMNS)]
    for r in rows:
        replicate = '' if r.replicate is None else str(r.replicate)
        lines.append('\t'.join(
            [r.sample_id, r.raw_file, r.treatment, r.fraction, replicate, r.batch]
        ))
    return '\n'.join(lines) + '\n'