'''
comMS experiment GUI: sample sheet panel
'''

# -- Import external dependencies
from pathlib import Path
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout

# -- Import internal functions
from comms.gui.models.experiment_state import ExperimentState
from comms.gui.models.sample_table import render_sample_sheet
from comms.gui.panels.groups import GroupsSubPanel
from comms.gui.panels.files import FilesSubPanel
from comms.gui.status import PanelStateTracker


# -- Define class SamplePanel to hold Groups/Files/Preview tabs + status tracking
class SamplePanel(QWidget):
    contentChanged = Signal()

    def __init__(self, state: ExperimentState, parent=None):
        super().__init__(parent)
        self._state = state
        self.tracker = PanelStateTracker(self)
        # Define layout
        layout = QVBoxLayout(self)
        self._groups = GroupsSubPanel(state)
        self._files = FilesSubPanel(state)
        layout.addWidget(self._groups)
        layout.addWidget(self._files, 1)
        # Emit contentChanged Signal when changed
        state.sample_model.contentChanged.connect(self._on_content_changed)

    def _on_content_changed(self) -> None:
        model = self._state.sample_model
        self.tracker.mark_changed(model.signature(), model.is_complete())
        self.contentChanged.emit()

    def is_complete(self) -> bool:
        return self._state.sample_model.is_complete()

    def sample_sheet_text(self) -> str:
        return render_sample_sheet(self._state.sample_model.rows())

    def data_files(self) -> list[str]:
        return [r.source_path for r in self._state.sample_model.rows() if r.source_path]

    def summary(self) -> str:
        n = len(self._state.sample_model.rows())
        return (f'{n} sample(s); {len(self._state.treatments)} treatment(s); '
                f'{len(self._state.fractions)} fraction(s)')

    # sync_tracker: refresh the tracker from current content (used before unified save)
    def sync_tracker(self) -> None:
        self._on_content_changed()

    def write(self, out_dir: Path) -> Path:
        path = out_dir / 'sample_sheet.tsv'
        path.write_text(self.sample_sheet_text(), encoding='utf-8')
        return path

    # -- load: populate the sample table and treatment/fraction groups from a loaded sample sheet
    def load(self, rows: list, treatments: list[str], fractions: list[str], data_files: list[str] | None = None) -> None:
        for t in treatments:
            self._state.add_treatment(t)
        for f in fractions:
            self._state.add_fraction(f)
        if data_files:
            by_name = {Path(p).name: str(p) for p in data_files}
            for row in rows:
                if not row.source_path:
                    match = by_name.get(row.raw_file)
                    if match:
                        row.source_path = match
        self._state.sample_model.set_rows(rows)