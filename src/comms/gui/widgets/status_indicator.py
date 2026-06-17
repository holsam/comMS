'''
comMS experiment GUI — status glyph painting (widget + icon)
'''

# -- Import external dependencies
from PySide6.QtCore import Qt, QSize, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QPixmap, QIcon
from PySide6.QtWidgets import QWidget

# -- Import internal functions
from comms.gui.status import PanelStatus

# -- Define glyph colours
_RED = QColor('#d9534f')
_AMBER = QColor('#f0ad4e')
_GREEN = QColor('#5cb85c')
_WHITE = QColor('white')


# -- _draw_cross: white cross inset within a filled disc
def _draw_cross(p: QPainter, box: QRectF) -> None:
    pen = QPen(_WHITE, max(box.width() * 0.12, 1.4))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    inset = box.adjusted(
        box.width() * 0.30, box.height() * 0.30,
        -box.width() * 0.30, -box.height() * 0.30
    )
    p.drawLine(inset.topLeft(), inset.bottomRight())
    p.drawLine(inset.bottomLeft(), inset.topRight())


# -- _draw_tick: white tick inset within a filled disc
def _draw_tick(p: QPainter, box: QRectF) -> None:
    pen = QPen(_WHITE, max(box.width() * 0.12, 1.4))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    w, h, x0, y0 = box.width(), box.height(), box.left(), box.top()
    p.drawPolyline([
        QPointF(x0 + w * 0.28, y0 + h * 0.52),
        QPointF(x0 + w * 0.44, y0 + h * 0.68),
        QPointF(x0 + w * 0.72, y0 + h * 0.34),
    ])


# -- paint_status: render the glyph for a PanelStatus into a rect
def paint_status(p: QPainter, box: QRectF, status: PanelStatus) -> None:
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    if status is PanelStatus.UNEDITED:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(_RED)
        p.drawEllipse(box)
        _draw_cross(p, box)
    elif status is PanelStatus.INCOMPLETE:
        p.setPen(QPen(_AMBER, 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(box)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(_AMBER)
        p.drawPie(box, 90 * 16, 180 * 16)
    else:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(_GREEN)
        p.drawEllipse(box)
        _draw_tick(p, box)


# -- status_icon: render a PanelStatus glyph as a QIcon (for tab icons)
def status_icon(status: PanelStatus, size: int = 16) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    paint_status(painter, QRectF(0, 0, size, size).adjusted(1, 1, -1, -1), status)
    painter.end()
    return QIcon(pixmap)


# -- StatusIndicator: small widget showing the glyph for a PanelStatus
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
        paint_status(painter, QRectF(self.rect()).adjusted(2, 2, -2, -2), self._status)
        painter.end()