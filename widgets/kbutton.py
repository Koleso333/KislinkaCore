"""
KButton — rounded button with press scale animation.
"""

from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import (
    Qt, pyqtProperty, QRectF,
)
from PyQt6.QtGui import QPainter, QColor

from core.animation import KAnimator, KEasing
from core.theme import ThemeManager
from core.fonts import Fonts


class KButton(QPushButton):

    def __init__(
        self,
        text: str = "",
        *,
        on_click=None,
        height: int = 44,
        font_size: int = 14,
        enabled: bool = True,
        parent=None,
    ):
        super().__init__(text, parent)

        self._font_size = font_size
        self._btn_height = height
        self._scale = 1.0

        self.setFont(Fonts.body(font_size))
        self.setFixedHeight(height)
        self.setMinimumWidth(80)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setEnabled(enabled)

        if on_click:
            self.clicked.connect(on_click)

        self._scale_anim = None

        self._tm = ThemeManager.instance()
        self._apply_theme()
        self._tm.changed.connect(self._apply_theme)

    def _get_scale(self) -> float:
        return self._scale

    def _set_scale(self, v: float):
        self._scale = v
        self.update()

    buttonScale = pyqtProperty(float, _get_scale, _set_scale)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2
        cy = self.height() / 2
        p.translate(cx, cy)
        p.scale(self._scale, self._scale)
        p.translate(-cx, -cy)

        t = self._tm
        if self.isEnabled():
            bg = QColor(t.fg)
            fg = QColor(t.bg)
        else:
            bg = QColor(t.disabled)
            fg = QColor(t.fg_dim)

        r = QRectF(0, 0, self.width(), self.height())
        p.setBrush(bg)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(r, 8, 8)

        p.setPen(fg)
        p.setFont(self.font())
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, self.text())
        p.end()

    def mousePressEvent(self, event):
        if self.isEnabled() and event.button() == Qt.MouseButton.LeftButton:
            self._animate_scale(0.95)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.isEnabled():
            self._animate_scale(1.0)
        super().mouseReleaseEvent(event)

    def _animate_scale(self, target: float):
        if self._scale_anim is not None:
            self._scale_anim.stop()
        self._scale_anim = KAnimator.start(
            self, b"buttonScale",
            start=self._scale, end=target,
            duration=100, easing=KEasing.IN_CUBIC,
            parent=self,
        )

    def setEnabled(self, enabled: bool):
        super().setEnabled(enabled)
        self.setCursor(
            Qt.CursorShape.PointingHandCursor if enabled
            else Qt.CursorShape.ArrowCursor
        )

    def _apply_theme(self):
        self.update()