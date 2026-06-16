'''
comMS experiment GUI: sample sheet panel
'''

# -- Import external dependencies
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QMessageBox

# -- Import internal functions
from comms.gui.models.experiment_state import ExperimentState
from comms.gui.panels.experiment_header import ExperimentHeaderPanel
from comms.gui.panels.groups import GroupsSubPanel
from comms.gui.panels.files import FilesSubPanel
from comms.gui.panels.preview import PreviewSubPanel, render_sample_sheet
from comms.gui.widgets.panel_title_bar import PanelTitleBar
from comms.gui.status import PanelStateTracker


# -- SamplePanel: title bar + Groups/Files/Preview tabs + status tracking + save
class SamplePanel(QWidget):
    def __init__(self, state: ExperimentState, header: ExperimentHeaderPanel, parent=None):
        super().__init__(parent)
        self._state = state
        self._header = header
        self.tracker = PanelStateTracker(self)

        layout = QVBoxLayout(self)
        self._title = PanelTitleBar('Sample Sheet')
        layout.addWidget(self._title)

        tabs = QTabWidget()
        self._groups = GroupsSubPanel(state)
        self._files = FilesSubPanel(state)
        self._preview = PreviewSubPanel()
        tabs.addTab(self._groups, 'Experiment Setup')
        tabs.addTab(self._files, 'Data Files')
        tabs.addTab(self._preview, 'Sample Sheet Preview')
        layout.addWidget(tabs)

        self._preview.save_button.clicked.connect(self._save)
        state.sample_model.contentChanged.connect(self._on_content_changed)
        header.changed.connect(self._refresh_save_button)
        self.tracker.statusChanged.connect(self._title.set_status)

    def _on_content_changed(self) -> None:
        model = self._state.sample_model
        self._preview.set_preview(render_sample_sheet(model.rows()))
        self.tracker.mark_changed(model.signature(), model.is_complete())
        self._refresh_save_button()

    def _refresh_save_button(self) -> None:
        valid_header = self._header.is_valid()
        self._preview.save_button.setEnabled(
            self._state.sample_model.is_complete() and valid_header)
        self._preview.save_button.setToolTip(
            '' if valid_header else 'Set an experiment name and directory first')

    def _save(self) -> None:
        out_dir = self._header.output_dir()
        if out_dir is None:
            return
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / 'sample_sheet.tsv'
        path.write_text(
            render_sample_sheet(self._state.sample_model.rows()), encoding='utf-8')
        self._header.write_metadata()
        self.tracker.mark_saved()
        QMessageBox.information(self, 'Saved', f'Sample sheet written to:\n{path}')