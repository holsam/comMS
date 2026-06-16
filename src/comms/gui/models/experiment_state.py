'''
comMS experiment GUI: shared experiment state (groups + sample table)
'''

# -- Import external dependencies
from PySide6.QtCore import QObject, Signal

# -- ExperimentState: shared treatment/fraction groups and the sample table model
class ExperimentState(QObject):
    groupsChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._treatments: list[str] = []
        self._fractions: list[str] = []
        # Import SampleTableModel from gui/models/sample_table.py
        from comms.gui.models.sample_table import SampleTableModel
        self.sample_model = SampleTableModel(self)

    @property
    def treatments(self) -> list[str]:
        return list(self._treatments)

    @property
    def fractions(self) -> list[str]:
        return list(self._fractions)

    def add_treatment(self, name: str) -> bool:
        return self._add(self._treatments, name)

    def add_fraction(self, name: str) -> bool:
        return self._add(self._fractions, name)

    def remove_treatment(self, name: str) -> None:
        self._remove(self._treatments, name)

    def remove_fraction(self, name: str) -> None:
        self._remove(self._fractions, name)

    def _add(self, store: list[str], name: str) -> bool:
        name = name.strip()
        if not name or name in store:
            return False
        store.append(name)
        self.groupsChanged.emit()
        return True

    def _remove(self, store: list[str], name: str) -> None:
        if name in store:
            store.remove(name)
            self.groupsChanged.emit()