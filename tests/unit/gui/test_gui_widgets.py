'''
Unit tests for src/comms/gui/widgets/*
'''

# -- Import external dependencies
import pytest
from unittest.mock import patch
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QComboBox, QStyleOptionViewItem, QWidget

# -- Import functions under test
from comms.gui.status import PanelStatus, PanelStateTracker
from comms.gui.widgets.status_indicator import StatusIndicator, status_icon
from comms.gui.widgets.combo_delegate import GroupComboDelegate

pytestmark = pytest.mark.usefixtures('qapp')


# -- Define tests for the status indicator widget
class TestStatusIndicator:
    def test_default_size(self):
        assert StatusIndicator().sizeHint() == QSize(18, 18)

    def test_set_status_for_each_state_does_not_raise(self):
        ind = StatusIndicator()
        for status in PanelStatus:
            ind.setStatus(status)

    def test_renders_without_error(self):
        ind = StatusIndicator()
        ind.setStatus(PanelStatus.SAVED)
        assert not ind.grab().isNull()


# -- Define tests for the status_icon helper
class TestStatusIcon:
    def test_returns_non_null_icon(self):
        assert not status_icon(PanelStatus.SAVED).isNull()

    def test_icon_renders_at_requested_size(self):
        icon = status_icon(PanelStatus.UNEDITED, size=16)
        assert icon.pixmap(QSize(16, 16)).width() == 16


# -- Define tests for the group combo-box delegate
class TestGroupComboDelegate:
    # -- Helper: a single-cell model holding an edit value
    def _index(self, value=''):
        model = QStandardItemModel(1, 1)
        model.setItem(0, 0, QStandardItem(value))
        return model, model.index(0, 0)

    # -- Helper: build an editor, keeping both parent and editor alive on self
    def _editor(self, delegate, index):
        self._parent_widget = QWidget()
        # Store the editor reference so it outlives the calling expression. Both refs are released after teardown_method drains the event queue.
        self._editor_widget = delegate.createEditor(
            self._parent_widget, QStyleOptionViewItem(), index
        )
        return self._editor_widget

    def teardown_method(self, method):
        # Process pending events (including any QTimer.singleShot callbacks) while _parent_widget and _editor_widget are still alive on self. Without this, the timer fires during pytest teardown after Qt has already destroyed the widgets, causing "C++ object already deleted".
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

    def test_create_editor_returns_combobox(self):
        delegate = GroupComboDelegate(lambda: ['MOCK', 'TREAT'])
        _, index = self._index()
        assert isinstance(self._editor(delegate, index), QComboBox)

    def test_editor_has_blank_first_item(self):
        delegate = GroupComboDelegate(lambda: ['MOCK'])
        _, index = self._index()
        assert self._editor(delegate, index).itemText(0) == ''

    def test_editor_populated_from_provider(self):
        delegate = GroupComboDelegate(lambda: ['MOCK', 'TREAT'])
        _, index = self._index()
        editor = self._editor(delegate, index)
        items = [editor.itemText(i) for i in range(editor.count())]
        assert items == ['', 'MOCK', 'TREAT']

    def test_editor_reflects_live_provider_options(self):
        options = ['MOCK']
        delegate = GroupComboDelegate(lambda: options)
        _, index = self._index()
        options.append('TREAT')
        editor = self._editor(delegate, index)
        items = [editor.itemText(i) for i in range(editor.count())]
        assert 'TREAT' in items

    def test_schedules_show_popup(self):
        delegate = GroupComboDelegate(lambda: ['MOCK'])
        _, index = self._index()
        with patch('comms.gui.widgets.combo_delegate.QTimer') as mock_timer:
            editor = self._editor(delegate, index)
        mock_timer.singleShot.assert_called_once()
        delay, callback = mock_timer.singleShot.call_args.args
        assert delay == 0
        assert callback == editor.showPopup

    def test_set_editor_data_selects_current_value(self):
        delegate = GroupComboDelegate(lambda: ['MOCK', 'TREAT'])
        _, index = self._index('TREAT')
        editor = self._editor(delegate, index)
        delegate.setEditorData(editor, index)
        assert editor.currentText() == 'TREAT'

    def test_set_editor_data_defaults_to_blank_when_absent(self):
        delegate = GroupComboDelegate(lambda: ['MOCK'])
        _, index = self._index('UNKNOWN')
        editor = self._editor(delegate, index)
        delegate.setEditorData(editor, index)
        assert editor.currentText() == ''

    def test_set_model_data_writes_current_text(self):
        delegate = GroupComboDelegate(lambda: ['MOCK', 'TREAT'])
        model, index = self._index()
        editor = self._editor(delegate, index)
        editor.setCurrentText('MOCK')
        delegate.setModelData(editor, model, index)
        assert model.data(index, Qt.ItemDataRole.EditRole) == 'MOCK'