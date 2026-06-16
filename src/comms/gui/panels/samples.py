'''
comMS experiment GUI: samples subpanel
'''

# -- Import external dependencies
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QListWidget, QGroupBox,
)

# -- Import internal functions
from comms.gui.models.experiment_state import ExperimentState

# -- Define class _SampleList to define a labelled add/list/remove control for one group type
class _SampleList(QGroupBox):
    def __init__(self, title, add_cb, remove_cb, items_cb, parent=None):
        super().__init__(title, parent)
        self._add_cb = add_cb
        self._remove_cb = remove_cb
        self._items_cb = items_cb

        layout = QVBoxLayout(self)
        entry_row = QHBoxLayout()
        self._entry = QLineEdit()
        self._entry.setPlaceholderText(f'New {title.lower()[:-1]}…')
        self._entry.returnPressed.connect(self._on_add)
        add_btn = QPushButton('Add')
        add_btn.clicked.connect(self._on_add)
        entry_row.addWidget(self._entry)
        entry_row.addWidget(add_btn)
        layout.addLayout(entry_row)

        self._list = QListWidget()
        layout.addWidget(self._list)
        remove_btn = QPushButton('Remove selected')
        remove_btn.clicked.connect(self._on_remove)
        layout.addWidget(remove_btn)
        self.refresh()

    def _on_add(self) -> None:
        if self._add_cb(self._entry.text()):
            self._entry.clear()

    def _on_remove(self) -> None:
        item = self._list.currentItem()
        if item is not None:
            self._remove_cb(item.text())

    def refresh(self) -> None:
        self._list.clear()
        self._list.addItems(self._items_cb())


# -- Define class SamplesSubPanel to hold two _SampleList controls for treatments and fractions
class SamplesSubPanel(QWidget):
    def __init__(self, state: ExperimentState, parent=None):
        super().__init__(parent)
        self._state = state
        layout = QHBoxLayout(self)
        self._treatments = _SampleList(
            'Treatments', state.add_treatment, state.remove_treatment,
            lambda: state.treatments,
        )
        self._fractions = _SampleList(
            'Fractions', state.add_fraction, state.remove_fraction,
            lambda: state.fractions,
        )
        layout.addWidget(self._treatments)
        layout.addWidget(self._fractions)
        state.groupsChanged.connect(self._refresh)

    def _refresh(self) -> None:
        self._treatments.refresh()
        self._fractions.refresh()