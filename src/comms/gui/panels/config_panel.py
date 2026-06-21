'''
comMS experiment GUI: comMS configuration panel
'''

# -- Import external dependencies
from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFileDialog, QFormLayout, QGroupBox, QCheckBox,
    QComboBox, QLineEdit, QPushButton, QTableWidget,
)

# -- Import internal functions
from comms.gui.status import PanelStateTracker
from comms.utils.settings import loadDefaultConfig
from comms.commands.config import (
    _apply_protocol_flags, _apply_organism, _apply_custom_mod, _writeConfigTo,
)

# -- Define class ConfigPanel to define a structured form mirroring `comms config set` with an additional analysis type activating the organism table
class ConfigPanel(QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tracker = PanelStateTracker(self)
        # Define layout
        layout = QVBoxLayout(self)
        # Row 1: modifications/instrument resolution 
        row1 = QHBoxLayout()
        row1.addWidget(self._build_mods_box(), 1, Qt.AlignmentFlag.AlignTop)
        row1.addWidget(self._build_resolution_box(), 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(row1)
        # Row 2: analysis type/organism table
        row2 = QHBoxLayout()
        row2.addWidget(self._build_analysis_type_box(), 0, Qt.AlignmentFlag.AlignTop)
        row2.addWidget(self._build_organism_box(), 1, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(row2)
        # Row 3: report setting
        layout.addWidget(self._build_report_box())
        layout.addStretch(1)
        # Update enabled boxes
        self._update_organism_enabled()
        self._update_report_fields_enabled()

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

    def _build_analysis_type_box(self) -> QGroupBox:
        box = QGroupBox('Analysis type')
        form = QFormLayout(box)
        # Analysis type combobox
        self._analysis = QComboBox()
        self._analysis.addItems(['Single species', 'Multispecies'])
        self._analysis.currentIndexChanged.connect(self._on_analysis_changed)
        # Shared PSM handler policy
        self._sharedpsm = QComboBox()
        self._sharedpsm.addItems(['Drop', 'Include'])
        form.addRow('Analysis Mode', self._analysis)
        form.addRow('Shared PSM handling policy', self._sharedpsm)
        return box

    def _build_organism_box(self) -> QGroupBox:
        self._org_box = QGroupBox('Organism patterns (per-organism FDR)')
        layout = QVBoxLayout(self._org_box)
        self._org_table = QTableWidget(0, 2)
        self._org_table.setHorizontalHeaderLabels(['Label', 'Pattern'])
        self._org_table.horizontalHeader().setStretchLastSection(True)
        self._org_table.itemChanged.connect(self._on_changed)
        layout.addWidget(self._org_table)
        buttons = QHBoxLayout()
        self._add_org_btn = QPushButton('Add organism')
        self._add_org_btn.clicked.connect(self._add_org_row)
        self._remove_org_btn = QPushButton('Remove selected')
        self._remove_org_btn.clicked.connect(self._remove_org_row)
        buttons.addStretch(1)
        buttons.addWidget(self._add_org_btn)
        buttons.addWidget(self._remove_org_btn)
        layout.addLayout(buttons)
        return self._org_box
    
    def _build_report_box(self) -> QGroupBox:
        box = QGroupBox('Report settings')
        outer = QVBoxLayout(box)
        self._report_enabled = QCheckBox('Create report?')
        self._report_enabled.setChecked(True)
        self._report_enabled.stateChanged.connect(self._on_report_enabled_changed)
        outer.addWidget(self._report_enabled)
        self._report_fields = QWidget()
        form = QFormLayout(self._report_fields)
        # Reference info file picker
        self._reference = QLineEdit()
        self._reference.setMinimumWidth(360)
        self._reference.setPlaceholderText('reference annotation TSV/CSV')
        self._reference.textChanged.connect(self._on_changed)
        ref_browse = QPushButton('Select file')
        ref_browse.clicked.connect(self._browse_reference)
        ref_row = QWidget()
        ref_layout = QHBoxLayout(ref_row)
        ref_layout.setContentsMargins(0, 0, 0, 0)
        ref_layout.addWidget(self._reference)
        ref_layout.addWidget(ref_browse)
        form.addRow('Reference info', ref_row)
        # Contaminant CSV picker
        self._contaminant = QLineEdit()
        self._contaminant.setMinimumWidth(360)
        self._contaminant.setPlaceholderText('contaminant list CSV')
        self._contaminant.textChanged.connect(self._on_changed)
        cont_browse = QPushButton('Select file')
        cont_browse.clicked.connect(self._browse_contaminant)
        cont_row = QWidget()
        cont_layout = QHBoxLayout(cont_row)
        cont_layout.setContentsMargins(0, 0, 0, 0)
        cont_layout.addWidget(self._contaminant)
        cont_layout.addWidget(cont_browse)
        form.addRow('Contaminants', cont_row)
        # Organism prefix (moved from ExperimentPanel)
        self._organism_prefix = QLineEdit()
        self._organism_prefix.setMinimumWidth(360)
        self._organism_prefix.setPlaceholderText('primary organism id prefix')
        self._organism_prefix.textChanged.connect(self._on_changed)
        form.addRow('Primary organism prefix', self._organism_prefix)

        outer.addWidget(self._report_fields)
        return box

    # -- analysis type --
    def _is_multispecies(self) -> bool:
        return self._analysis.currentIndex() == 1

    def _on_analysis_changed(self, *args) -> None:
        self._update_organism_enabled()
        self._on_changed()

    def _update_organism_enabled(self) -> None:
        self._sharedpsm.setEnabled(self._is_multispecies())
        self._org_box.setEnabled(self._is_multispecies())

    def analysis_mode(self) -> str:
        return 'multi' if self._is_multispecies() else 'single'
    
    def shared_policy(self) -> str:
        return 'drop' if self._sharedpsm.currentIndex() == 0 else 'include'

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
    
    def has_organism_patterns(self) -> bool:
        '''True when at least one organism row has both a label and a pattern'''
        return any(label and pattern for label, pattern in self._organism_rows())

    # -- _organisms_complete: a row is valid only if both label and pattern are set (or both empty)
    def _organisms_complete(self) -> bool:
        if not self._is_multispecies():
            return True
        rows = self._organism_rows()
        if not any(label and pattern for label, pattern in rows):
            return False
        return all(bool(label) == bool(pattern) for label, pattern in rows)
    
    # -- report box helpers --
    def _on_report_enabled_changed(self, *args) -> None:
        self._update_report_fields_enabled()
        self._on_changed()

    def _update_report_fields_enabled(self) -> None:
        self._report_fields.setEnabled(self._report_enabled.isChecked())

    def _browse_reference(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, 'Select reference info file', '',
            'Tabular files (*.tsv *.csv *.txt);;All files (*)')
        if path:
            self._reference.setText(path)

    def _browse_contaminant(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, 'Select contaminant list', '',
            'CSV files (*.csv);;All files (*)')
        if path:
            self._contaminant.setText(path)

    def organism_prefix(self) -> str:
        return self._organism_prefix.text().strip()

    def report_enabled(self) -> bool:
        return self._report_enabled.isChecked()

    def reference_path(self) -> Path | None:
        text = self._reference.text().strip()
        return Path(text) if text else None

    def contaminant_path(self) -> Path | None:
        text = self._contaminant.text().strip()
        return Path(text) if text else None
    # -- state --
    def _signature(self):
        return (
            self._iodo.isChecked(), self._ox.isChecked(), self._phos.isChecked(),
            self._n_cyc.isChecked(), self._n_ace.isChecked(), self._clip_met.isChecked(),
            self._custom.text().strip(), self._res.currentIndex(),
            tuple(self._organism_rows()),
            self._report_enabled.isChecked(),
            self._reference.text().strip(),
            self._contaminant.text().strip(),
            self._organism_prefix.text().strip(),
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
        if self._is_multispecies():
            orgs = [label for label, pattern in self._organism_rows() if label and pattern]
            org_text = ', '.join(orgs) if orgs else 'none'
            mode = 'multispecies'
        else:
            org_text = 'n/a (single species)'
            mode = 'single species'
        report = ('report: enabled' if self._report_enabled.isChecked() else 'report: disabled')
        return (f'{mode}; resolution: {res}; '
                f'mods: {", ".join(mods) if mods else "none"}; organisms: {org_text}; {report}')

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
        organisms = {}
        if self._is_multispecies():
            organisms = {
                label: pattern for label, pattern in self._organism_rows() if label and pattern
            }
            cfg['percolator']['shared_psm'] = self.shared_policy()
        cfg = _apply_organism(cfg, organisms)
        cfg.setdefault('index', {})
        cfg['index']['custom_mods'] = ''
        custom = self._custom.text().strip()
        if custom:
            for entry in [e.strip() for e in custom.split(',') if e.strip()]:
                cfg['index']['custom_mods'] = _apply_custom_mod(
                    cfg['index']['custom_mods'], entry)
        return cfg
    
    # sync_tracker: refresh the tracker from current content (used before unified save)
    def sync_tracker(self) -> None:
        self._on_changed()

    def write(self, out_dir: Path) -> Path:
        path = out_dir / 'config.toml'
        _writeConfigTo(self._build_config(), path)
        return path