'''
comMS experiment GUI: status indicator glyph
'''

# -- Import external dependencies
from PySide6.QtCore import Qt, QSize, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtWidgets import QWidget

# -- Import internal functions
from comms.gui.status import PanelStatus

# -- Define glyph colours
_RED = QColor('#d9534f')
_AMBER = QColor('#f0ad4e')
_GREEN = QColor('#5cb85c')

# -- Define class StatusIndicator as a small colour glyph reflecting a PanelStatus
class StatusIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._status = PanelStatus.UNEDITED
        self.setFixedSize(18, 18)

    def sizeHint(self) -> QSize:
        return QSize(18, 18)

    def setStatus(self, status: PanelStatus) -> None:
        if status is not self._status:
            self._status = status
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        box = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        if self._status is PanelStatus.UNEDITED:
            self._paint_cross(painter, box)
        elif self._status is PanelStatus.INCOMPLETE:
            self._paint_half(painter, box)
        elif self._status is PanelStatus.COMPLETE_UNSAVED:
            self._paint_full(painter, box)
        else:
            self._paint_tick(painter, box)
        painter.end()

    def _paint_cross(self, p: QPainter, box: QRectF) -> None:
        pen = QPen(_RED, 2.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawLine(box.topLeft(), box.bottomRight())
        p.drawLine(box.bottomLeft(), box.topRight())

    def _paint_half(self, p: QPainter, box: QRectF) -> None:
        p.setPen(QPen(_AMBER, 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(box)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(_AMBER)
        p.drawPie(box, 90*16, 180*16)

    def _paint_full(self, p: QPainter, box: QRectF) -> None:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(_AMBER)
        p.drawEllipse(box)

    def _paint_tick(self, p: QPainter, box: QRectF) -> None:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(_GREEN)
        p.drawEllipse(box)
        pen = QPen(QColor('white'), 2.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        w, h, x0, y0 = box.width(), box.height(), box.left(), box.top()
        p.drawPolyline([
            QPointF(x0 + w*0.28, y0 + h*0.52),
            QPointF(x0 + w*0.44, y0 + h*0.68),
            QPointF(x0 + w*0.72, y0 + h*0.34),
        ])