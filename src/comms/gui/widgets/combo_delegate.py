'''
comMS experiment GUI: combo-box delegate to read live group options
'''

# -- Import external dependencies
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QStyledItemDelegate, QComboBox


# -- Define class GroupComboDelegate to define a dropdown editor whose options come from a provider callable
class GroupComboDelegate(QStyledItemDelegate):
    def __init__(self, options_provider, parent=None):
        super().__init__(parent)
        self._options_provider = options_provider

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.addItem('')
        combo.addItems(self._options_provider())
        return combo

    def setEditorData(self, editor, index):
        current = index.data(Qt.ItemDataRole.EditRole) or ''
        pos = editor.findText(current)
        editor.setCurrentIndex(pos if pos >= 0 else 0)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.ItemDataRole.EditRole)