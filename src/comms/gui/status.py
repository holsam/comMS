'''
comMS experiment GUI — panel status tracking
'''

# -- Import external dependencies
from enum import Enum, auto
from PySide6.QtCore import QObject, Signal

# -- Define class PanelStatus to define the four states a savable panel can be in:
# --    - UNEDITED: no change since window opened
# --    - INCOMPLETE: edited, required fields still missing
# --    - COMPLETE_UNSAVED: all required fields present, not yet saved
# --    - SAVED: saved and unchanged since
class PanelStatus(Enum):
    UNEDITED = auto()
    INCOMPLETE = auto()
    COMPLETE_UNSAVED = auto()
    SAVED = auto()

# -- Define class PanelStateTracker to record edited/complete/saved state and report a PanelStatus
class PanelStateTracker(QObject):
    statusChanged = Signal(object)
    def __init__(self, parent=None):
        super().__init__(parent)
        self._edited = False
        self._complete = False
        self._current_signature = None
        self._saved_signature = None
    # -- mark_changed: record the current content snapshot and whether it is complete
    def mark_changed(self, signature, complete: bool) -> None:
        self._edited = True
        self._current_signature = signature
        self._complete = complete
        self.statusChanged.emit(self.status)
    # -- mark_saved: record that the current content has been written to disk
    def mark_saved(self) -> None:
        self._saved_signature = self._current_signature
        self.statusChanged.emit(self.status)
    
    @property
    def status(self) -> PanelStatus:
        if not self._edited:
            return PanelStatus.UNEDITED
        if (self._complete
                and self._saved_signature is not None
                and self._current_signature == self._saved_signature):
            return PanelStatus.SAVED
        if self._complete:
            return PanelStatus.COMPLETE_UNSAVED
        return PanelStatus.INCOMPLETE

    @property
    def is_saveable(self) -> bool:
        return self.status in (PanelStatus.COMPLETE_UNSAVED, PanelStatus.SAVED)