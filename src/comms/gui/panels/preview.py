'''
comMS experiment GUI: preview subpanel (to render and save the sample sheet)
'''

# -- Import external dependencies
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QPushButton

# -- Import internal functions
from comms.gui.models.sample_table import COLUMNS

# -- render_sample_sheet: build the TSV text for a list of SampleRow
def render_sample_sheet(rows) -> str:
    lines = ['\t'.join(COLUMNS)]
    for r in rows:
        replicate = '' if r.replicate is None else str(r.replicate)
        lines.append('\t'.join(
            [r.sample_id, r.raw_file, r.treatment, r.fraction, replicate, r.batch]
        ))
    return '\n'.join(lines) + '\n'

# -- Define class PreviewSubPanel to render a read-only TSV preview with a save button
class PreviewSubPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        self._text.setFont(QFont('monospace'))
        layout.addWidget(self._text)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self.save_button = QPushButton('Save sample sheet')
        self.save_button.setEnabled(False)
        button_row.addWidget(self.save_button)
        layout.addLayout(button_row)

    def set_preview(self, text: str) -> None:
        self._text.setPlainText(text)