'''
comMS experiment GUI: save experiment tab (for summary + unified save)
'''

# -- Import external dependencies
from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QLabel, QPushButton, QPlainTextEdit, QMessageBox,
)

# -- Import internal functions
from comms.gui.panels.experiment_panel import ExperimentPanel
from comms.gui.panels.sample_panel import SamplePanel
from comms.gui.panels.config_panel import ConfigPanel

# -- Define class SavePanel to summarises the three tabs and writes all outputs at once
class SavePanel(QWidget):
    saved = Signal()

    def __init__(self, experiment: ExperimentPanel, sample: SamplePanel, config: ConfigPanel, parent=None):
        super().__init__(parent)
        self._experiment = experiment
        self._sample = sample
        self._config = config

        layout = QVBoxLayout(self)

        summary_box = QGroupBox('Summary')
        form = QFormLayout(summary_box)
        self._exp_label = QLabel()
        self._sample_label = QLabel()
        self._config_label = QLabel()
        form.addRow('Experiment Information:', self._exp_label)
        form.addRow('Sample Information:', self._sample_label)
        form.addRow('Analysis Information:', self._config_label)
        layout.addWidget(summary_box)

        preview_box = QGroupBox('Sample sheet preview')
        preview_layout = QVBoxLayout(preview_box)
        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)
        preview_layout.addWidget(self._preview)
        layout.addWidget(preview_box, 1)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self.save_button = QPushButton('Save Experiment')
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self._save_all)
        button_row.addWidget(self.save_button)
        layout.addLayout(button_row)

    # -- refresh: rebuild the summary and re-evaluate the save button
    def refresh(self) -> None:
        out_dir = self._experiment.output_dir()
        name = self._experiment.experiment_name() or '(unnamed)'
        self._exp_label.setText(
            f'{name}  →  {out_dir}' if out_dir else f'{name}  →  (no directory set)')
        self._sample_label.setText(self._sample.summary())
        self._config_label.setText(self._config.summary())
        self._preview.setPlainText(self._sample.sample_sheet_text())
        self.save_button.setEnabled(self._all_complete())
        self.save_button.setToolTip(
            '' if self._all_complete() else 'Complete all three tabs before saving')

    def _all_complete(self) -> bool:
        return (self._experiment.is_valid()
                and self._sample.is_complete()
                and self._config.is_complete())

    def _save_all(self) -> None:
        out_dir = self._experiment.output_dir()
        if out_dir is None:
            return
        out_dir.mkdir(parents=True, exist_ok=True)
        sheet_path = self._sample.write(out_dir)
        config_path = self._config.write(out_dir)
        meta_path = self._experiment.write_metadata(
            out_dir,
            files={'sample_sheet': sheet_path, 'config': config_path},
        )
        self._experiment.tracker.mark_saved()
        self._sample.tracker.mark_saved()
        self._config.tracker.mark_saved()
        self.saved.emit()
        QMessageBox.information(
            self, 'Experiment saved',
            'Experiment saved.\n\n'
            f'Sample sheet: {sheet_path}\n'
            f'Configuration: {config_path}\n'
            f'Metadata: {meta_path}')