'''
comMS experiment GUI: command-readiness panel
'''

# -- Import external dependencies
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

# -- Import internal functions
from comms.utils.installrdeps import check_r_dependencies, install_r_dependencies
from comms.utils.paths import repoBinDir
from comms.utils.readiness import COMMANDS, missing_requirements
from comms.utils.validate import probe_crux, probe_trfp
from comms.gui.widgets.status_indicator import StatusIndicator
from comms.gui.status import PanelStatus


# -- Define class CommandReadinessPanel to show, per command, whether the experiment can run it
class CommandReadinessPanel(QWidget):
    '''
    A read-only summary: one row per comMS command with a status glyph and the inputs still missing; recomputed via refresh() when a source panel changes
    '''
    def __init__(self, experiment, sample, config, parent=None):
        super().__init__(parent)
        self._experiment = experiment
        self._sample = sample
        self._config = config
        # -- cached dependency state, refreshed by _refresh_dependencies() rather than on every refresh()
        self._r_deps_status: dict | None = None
        self._crux_found = False
        self._trfp_found = False
        layout = QVBoxLayout(self)
        box = QGroupBox('Command readiness')
        grid = QGridLayout(box)
        grid.setColumnStretch(2, 1)

        self._indicators: dict[str, StatusIndicator] = {}
        self._details: dict[str, QLabel] = {}
        for row, command in enumerate(COMMANDS):
            indicator = StatusIndicator()
            name = QLabel(command)
            detail = QLabel()
            detail.setStyleSheet('color: gray;')
            grid.addWidget(indicator, row, 0, Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(name, row, 1)
            grid.addWidget(detail, row, 2)
            self._indicators[command] = indicator
            self._details[command] = detail

        deps_box = QGroupBox('Dependencies')
        deps_layout = QVBoxLayout(deps_box)
        summary_row = QHBoxLayout()
        self._deps_indicator = StatusIndicator()
        self._deps_label = QLabel()
        summary_row.addWidget(self._deps_indicator, 0, Qt.AlignmentFlag.AlignVCenter)
        summary_row.addWidget(self._deps_label, 1)
        deps_layout.addLayout(summary_row)

        buttons_row = QHBoxLayout()
        self._install_deps_btn = QPushButton('Install R dependencies')
        self._install_deps_btn.clicked.connect(self._install_deps)
        self._locate_trfp_btn = QPushButton('Locate TRFP…')
        self._locate_trfp_btn.clicked.connect(self._set_bin_dir)
        self._locate_crux_btn = QPushButton('Locate Crux…')
        self._locate_crux_btn.clicked.connect(self._set_bin_dir)
        buttons_row.addWidget(self._install_deps_btn)
        buttons_row.addWidget(self._locate_trfp_btn)
        buttons_row.addWidget(self._locate_crux_btn)
        deps_layout.addLayout(buttons_row)

        layout.addWidget(deps_box)
        layout.addWidget(box)
        layout.addStretch(1)
        self._refresh_dependencies()
        self.refresh()

    # -- _state: gather the booleans the readiness model needs from the source panels and cached dependency state
    def _state(self) -> dict:
        return dict(
            has_data=len(self._sample.data_files()) > 0,
            has_database=bool(self._experiment.database_path()),
            has_sample_sheet=self._sample.is_complete(),
            has_organism_prefix=bool(self._config.organism_prefix()),
            multispecies=self._config.analysis_mode() == 'multi',
            has_organism_tags=self._config.has_organism_patterns(),
            has_trfp=self._trfp_found,
            has_crux=self._crux_found,
            has_r_deps=self._r_deps_status is not None and not self._r_deps_status['missing'],
        )

    # -- refresh: recompute command-row readiness and repaint each row (reads cached dependency state; call refresh_dependencies() to re-probe)
    def refresh(self) -> None:
        missing = missing_requirements(**self._state())
        for command in COMMANDS:
            gaps = list(dict.fromkeys(missing[command]))
            ready = not gaps
            self._indicators[command].setStatus(
                PanelStatus.COMPLETE if ready else PanelStatus.UNEDITED
            )
            text = 'ready' if ready else 'needs ' + ', '.join(gaps)
            self._details[command].setText(text)
            tooltip = 'Ready to run' if ready else 'Missing: ' + ', '.join(gaps)
            self._indicators[command].setToolTip(tooltip)
            self._details[command].setToolTip(tooltip)

    # -- refresh_dependencies: public entry point for main_window.py to call after the bin_dir field changes
    def refresh_dependencies(self) -> None:
        self._refresh_dependencies()
        self.refresh()

    # -- _refresh_dependencies: re-probe R deps / Crux / TRFP, repaint the Dependencies box, and cache results for _state()
    def _refresh_dependencies(self) -> None:
        self._r_deps_status = check_r_dependencies()
        bin_dir = repoBinDir(experiment_bin_dir=self._experiment.bin_dir())
        self._crux_found = probe_crux(bin_dir) is not None
        self._trfp_found = probe_trfp(bin_dir) is not None
        parts = []
        if self._r_deps_status is None:
            parts.append('Rscript not found on PATH')
        elif self._r_deps_status['missing']:
            parts.append(f"{len(self._r_deps_status['missing'])} R package(s) missing")
        else:
            parts.append('R packages OK')
        parts.append('Crux OK' if self._crux_found else 'Crux not found')
        parts.append('TRFP OK' if self._trfp_found else 'TRFP not found')
        self._deps_label.setText(' · '.join(parts))
        tooltip_lines = [f'Searched for Crux/TRFP in: {bin_dir}']
        if self._r_deps_status and self._r_deps_status['missing']:
            tooltip_lines.append(f"Missing R packages: {', '.join(self._r_deps_status['missing'])}")
        tooltip = '\n'.join(tooltip_lines)
        self._deps_label.setToolTip(tooltip)
        r_ok = self._r_deps_status is not None and not self._r_deps_status['missing']
        all_ok = r_ok and self._crux_found and self._trfp_found
        none_ok = not r_ok and not self._crux_found and not self._trfp_found
        if all_ok:
            self._deps_indicator.setStatus(PanelStatus.COMPLETE)
        elif none_ok:
            self._deps_indicator.setStatus(PanelStatus.UNEDITED)
        else:
            self._deps_indicator.setStatus(PanelStatus.INCOMPLETE)
        self._deps_indicator.setToolTip(tooltip)

        can_install = self._r_deps_status is not None and bool(self._r_deps_status['missing'])
        self._install_deps_btn.setEnabled(can_install)

    # -- _set_bin_dir: open a directory picker and write the chosen path into the experiment panel's bin_dir field
    def _set_bin_dir(self) -> None:
        current = self._experiment.bin_dir()
        start_dir = str(current) if current else ''
        chosen = QFileDialog.getExistingDirectory(
            self, 'Select bin directory (containing Crux and/or ThermoRawFileParser)', start_dir,
        )
        if not chosen:
            return
        self._experiment.set_bin_dir(Path(chosen))

    def _install_deps(self) -> None:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            ok = install_r_dependencies()
        finally:
            QApplication.restoreOverrideCursor()
        self.refresh_dependencies()
        if ok:
            QMessageBox.information(self, 'R dependencies', 'All comms report R dependencies are installed.')
        else:
            QMessageBox.warning(self, 'R dependencies', 'Some R dependencies could not be installed. Check the terminal log for details.')