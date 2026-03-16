from __future__ import annotations

from PyQt6.QtWidgets import QCheckBox
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen

from core.theme import ThemeManager
from core.fonts import Fonts
from widgets.kicon import load_svg_icon


class KCheckbox(QCheckBox):
    def __init__(
        self,
        text: str = "",
        *,
        checked: bool = False,
        font_size: int = 14,
        box_size: int = 18,
        parent=None,
    ):
        super().__init__(text, parent)

        self._box = max(12, int(box_size))

        self.setFont(Fonts.body(font_size))
        self.setChecked(checked)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("background: transparent;")
        self.setMinimumHeight(max(self._box + 6, 24))

        self._tm = ThemeManager.instance()
        self._apply_theme()
        self._tm.changed.connect(self._apply_theme)

    def _apply_theme(self) -> None:
        # Painted manually; no hover effects.
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        t = self._tm
        enabled = self.isEnabled()
        checked = self.isChecked()

        box = self._box
        gap = 10
        radius = 4

        y = (self.height() - box) / 2
        box_rect = QRectF(0, y, box, box)
        text_rect = QRectF(box + gap, 0, max(0.0, self.width() - (box + gap)), self.height())

        # colors
        text_color = QColor(t.fg if enabled else t.fg_dim)
        border_color = QColor(t.border if enabled else t.disabled)
        bg_color = QColor(t.bg_alt)

        if checked:
            fill_color = QColor(t.fg if enabled else t.disabled)
        else:
            fill_color = bg_color

        # box
        p.setPen(QPen(border_color, 1.5))
        p.setBrush(fill_color)
        p.drawRoundedRect(box_rect, radius, radius)

        # icon
        icon_size = max(10, int(box * 0.70))
        icon_x = box_rect.center().x() - icon_size / 2
        icon_y = box_rect.center().y() - icon_size / 2
        icon_target = QRectF(icon_x, icon_y, icon_size, icon_size)

        if checked:
            # filled box + checkmark
            ico_color = t.bg if enabled else t.bg_alt
            ico = load_svg_icon("check", color=ico_color, size=icon_size, auto_invert=False)
        else:
            # empty box + cross
            ico_color = t.fg if enabled else t.fg_dim
            ico = load_svg_icon("close", color=ico_color, size=icon_size, auto_invert=False)

        pm = ico.pixmap(icon_size, icon_size)
        p.drawPixmap(icon_target.toRect(), pm)

        # text
        p.setPen(text_color)
        p.setFont(self.font())
        p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text())

        p.end()
