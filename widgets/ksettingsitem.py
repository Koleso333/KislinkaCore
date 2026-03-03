"""
KSettingsItem — iOS-style settings row with label, optional icon, arrow.

    ┌─────────────────────────────────────┐
    │  ⚙  Theme                       →  │
    └─────────────────────────────────────┘
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QRectF
from PyQt6.QtGui import QFont, QPainter, QColor

from core.theme import ThemeManager
from widgets.kicon import load_svg_icon


class KSettingsItem(QWidget):
    """Clickable settings row."""

    clicked = pyqtSignal()

    ITEM_HEIGHT = 52

    def __init__(
        self,
        text: str,
        icon_name: str = "",
        show_arrow: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        self._text = text
        self._icon_name = icon_name
        self._show_arrow = show_arrow
        self._hovered = False
        self._pressed = False

        self.setFixedHeight(self.ITEM_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._tm = ThemeManager.instance()
        self._tm.changed.connect(self.update)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self._tm
        w = self.width()
        h = self.height()

        # background
        if self._pressed:
            bg = QColor(t.hover)
        elif self._hovered:
            bg = QColor(t.hover)
            bg.setAlpha(120)
        else:
            bg = QColor(t.bg_alt)

        rect = QRectF(0, 0, w, h)
        p.setBrush(bg)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(rect, 10, 10)

        # icon
        x_offset = 16
        if self._icon_name:
            icon = load_svg_icon(self._icon_name, color=t.fg, size=20)
            pixmap = icon.pixmap(20, 20)
            y_icon = (h - 20) // 2
            p.drawPixmap(x_offset, y_icon, pixmap)
            x_offset += 32

        # text
        p.setPen(QColor(t.fg))
        p.setFont(QFont("Roboto", 14, QFont.Weight.Bold))
        text_rect = QRectF(x_offset, 0, w - x_offset - 40, h)
        p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter, self._text)

        # arrow →
        if self._show_arrow:
            p.setPen(QColor(t.fg_dim))
            p.setFont(QFont("Roboto", 16, QFont.Weight.Bold))
            arrow_rect = QRectF(w - 36, 0, 24, h)
            p.drawText(arrow_rect, Qt.AlignmentFlag.AlignCenter, "›")

        # bottom separator
        p.setPen(QColor(t.hover))
        p.drawLine(16, h - 1, w - 16, h - 1)

        p.end()

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self.update()

    def mouseReleaseEvent(self, event):
        if self._pressed:
            self._pressed = False
            self.update()
            if self.rect().contains(event.pos().toPoint()):
                self.clicked.emit()