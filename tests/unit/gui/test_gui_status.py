'''
Unit tests for src/comms/gui/status.py
'''

# -- Import external dependencies
import pytest
from PySide6.QtCore import QSize

# -- Import functions under test
from comms.gui.status import PanelStatus, PanelStateTracker

pytestmark = pytest.mark.usefixtures('qapp')


# -- Define tests for the PanelStateTracker state machine
class TestPanelStateTracker:
    def test_starts_unedited(self):
        assert PanelStateTracker().status is PanelStatus.UNEDITED

    def test_incomplete_after_partial_change(self):
        t = PanelStateTracker()
        t.mark_changed(('a',), complete=False)
        assert t.status is PanelStatus.INCOMPLETE

    def test_complete_after_complete_change(self):
        t = PanelStateTracker()
        t.mark_changed(('a',), complete=True)
        assert t.status is PanelStatus.COMPLETE

    def test_saved_after_mark_saved(self):
        t = PanelStateTracker()
        t.mark_changed(('a',), complete=True)
        t.mark_saved()
        assert t.status is PanelStatus.SAVED

    def test_edit_after_save_returns_to_unsaved(self):
        t = PanelStateTracker()
        t.mark_changed(('a',), complete=True)
        t.mark_saved()
        t.mark_changed(('b',), complete=True)
        assert t.status is PanelStatus.COMPLETE

    def test_reverting_to_saved_signature_is_saved(self):
        t = PanelStateTracker()
        t.mark_changed(('a',), complete=True)
        t.mark_saved()
        t.mark_changed(('b',), complete=True)
        t.mark_changed(('a',), complete=True)
        assert t.status is PanelStatus.SAVED

    def test_status_changed_signal_emitted(self):
        t = PanelStateTracker()
        seen = []
        t.statusChanged.connect(lambda s: seen.append(s))
        t.mark_changed(('a',), complete=True)
        assert seen[-1] is PanelStatus.COMPLETE

    def test_is_saveable_true_for_complete_and_saved(self):
        t = PanelStateTracker()
        t.mark_changed(('a',), complete=True)
        assert t.is_saveable is True
        t.mark_saved()
        assert t.is_saveable is True

    def test_is_saveable_false_for_unedited_and_incomplete(self):
        t = PanelStateTracker()
        assert t.is_saveable is False
        t.mark_changed(('a',), complete=False)
        assert t.is_saveable is False
