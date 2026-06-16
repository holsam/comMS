'''
comMS experiment GUI: comMS configuration panel
'''

# -- Import external dependencies
from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QCheckBox, QComboBox, QLineEdit, QPushButton, QTableWidget,
)

# -- Import internal functions
from comms.gui.status import PanelStateTracker
from comms.utils.settings import loadDefaultConfig
from comms.commands.config import (
    _apply_protocol_flags, _apply_organism, _apply_custom_mod, _writeConfigTo,
)


# -- Define class ConfigPanel to define a structured form mirroring `comms config set`
class ConfigPanel(QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tracker = PanelStateTracker(self)
        # Define layout
        layout = QVBoxLayout(self)
        layout.addWidget(self._build_mods_box())
        layout.addWidget(self._build_resolution_box())
        layout.addWidget(self._build_organism_box())
        layout.addStretch(1)

    # -- form construction --
    def _build_mods_box(self) -> QGroupBox:
        box = QGroupBox('Modifications')
        form = QFormLayout(box)
        self._iodo = QCheckBox('Cysteine carbamidomethylation (static)')
        self._ox = QCheckBox('Methionine oxidation (variable)')
        self._ox.setChecked(True)
        self._phos = QCheckBox('STY phosphorylation (variable)')
        self._n_cyc = QCheckBox('N-terminal Gln cyclisation')
        self._n_cyc.setChecked(True)
        self._n_ace = QCheckBox('Protein N-terminal acetylation')
        self._n_ace.setChecked(True)
        self._clip_met = QCheckBox('Clip N-terminal methionine')
        self._clip_met.setChecked(True)
        for w in (self._iodo, self._ox, self._phos, self._n_cyc, self._n_ace, self._clip_met):
            form.addRow(w)
            w.stateChanged.connect(self._on_changed)
        self._custom = QLineEdit()
        self._custom.setPlaceholderText('Custom mods, comma separated')
        self._custom.textChanged.connect(self._on_changed)
        form.addRow('Custom', self._custom)
        return box

    def _build_resolution_box(self) -> QGroupBox:
        box = QGroupBox('Instrument resolution')
        form = QFormLayout(box)
        self._res = QComboBox()
        self._res.addItems(['High-res (Orbitrap)', 'Low-res (ion trap)'])
        self._res.currentIndexChanged.connect(self._on_changed)
        form.addRow('Mode', self._res)
        return box

    def _build_organism_box(self) -> QGroupBox:
        box = QGroupBox('Organism patterns (per-organism FDR)')
        layout = QVBoxLayout(box)
        self._org_table = QTableWidget(0, 2)
        self._org_table.setHorizontalHeaderLabels(['Label', 'Pattern'])
        self._org_table.horizontalHeader().setStretchLastSection(True)
        self._org_table.itemChanged.connect(self._on_changed)
        layout.addWidget(self._org_table)
        buttons = QHBoxLayout()
        add_btn = QPushButton('Add organism')
        add_btn.clicked.connect(self._add_org_row)
        remove_btn = QPushButton('Remove selected')
        remove_btn.clicked.connect(self._remove_org_row)
        buttons.addStretch(1)
        buttons.addWidget(add_btn)
        buttons.addWidget(remove_btn)
        layout.addLayout(buttons)
        return box

    # -- organism table helpers --
    def _add_org_row(self) -> None:
        self._org_table.insertRow(self._org_table.rowCount())
        self._on_changed()

    def _remove_org_row(self) -> None:
        row = self._org_table.currentRow()
        if row >= 0:
            self._org_table.removeRow(row)
            self._on_changed()

    def _organism_rows(self):
        result = []
        for i in range(self._org_table.rowCount()):
            label_item = self._org_table.item(i, 0)
            pattern_item = self._org_table.item(i, 1)
            label = label_item.text().strip() if label_item else ''
            pattern = pattern_item.text().strip() if pattern_item else ''
            result.append((label, pattern))
        return result

    # -- _organisms_complete: a row is valid only if both label and pattern are set (or both empty)
    def _organisms_complete(self) -> bool:
        return all(bool(label) == bool(pattern) for label, pattern in self._organism_rows())

    # -- state --
    def _signature(self):
        return (
            self._iodo.isChecked(), self._ox.isChecked(), self._phos.isChecked(),
            self._n_cyc.isChecked(), self._n_ace.isChecked(), self._clip_met.isChecked(),
            self._custom.text().strip(), self._res.currentIndex(),
            tuple(self._organism_rows()),
        )

    def _on_changed(self, *args) -> None:
        self.tracker.mark_changed(self._signature(), self._organisms_complete())
        self.changed.emit()

    def is_complete(self) -> bool:
        return self._organisms_complete()

    def summary(self) -> str:
        mods = []
        if self._iodo.isChecked():
            mods.append('carbamidomethyl (C)')
        if self._ox.isChecked():
            mods.append('ox (M)')
        if self._phos.isChecked():
            mods.append('phospho (STY)')
        if self._n_cyc.isChecked():
            mods.append('Gln cyclisation')
        if self._n_ace.isChecked():
            mods.append('N-term acetyl')
        res = 'low-res' if self._res.currentIndex() == 1 else 'high-res'
        orgs = [label for label, pattern in self._organism_rows() if label and pattern]
        return (f'Resolution: {res}; '
                f'mods: {", ".join(mods) if mods else "none"}; '
                f'organisms: {", ".join(orgs) if orgs else "none"}')

    # -- build config file and save --
    def _build_config(self) -> dict:
        cfg = loadDefaultConfig()
        cfg = _apply_protocol_flags(
            cfg,
            iodo=self._iodo.isChecked(),
            ox=self._ox.isChecked(),
            phos=self._phos.isChecked(),
            n_cyc=self._n_cyc.isChecked(),
            n_ace=self._n_ace.isChecked(),
            clip_met=self._clip_met.isChecked(),
            low_res=(self._res.currentIndex() == 1),
        )
        organisms = {
            label: pattern for label, pattern in self._organism_rows() if label and pattern
        }
        cfg = _apply_organism(cfg, organisms)
        cfg.setdefault('search', {})
        cfg['search']['custom_mods'] = ''
        custom = self._custom.text().strip()
        if custom:
            for entry in [e.strip() for e in custom.split(',') if e.strip()]:
                cfg['search']['custom_mods'] = _apply_custom_mod(
                    cfg['search']['custom_mods'], entry)
        return cfg

    def write(self, out_dir: Path) -> Path:
        path = out_dir / 'config.toml'
        _writeConfigTo(self._build_config(), path)
        return path