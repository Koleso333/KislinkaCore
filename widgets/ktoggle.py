"""
KToggle — iOS-style toggle switch.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import (
    Qt, QRectF, QPropertyAnimation, QEasingCurve,
    pyqtSignal, pyqtProperty,
)
from PyQt6.QtGui import QPainter, QColor

from core.theme import ThemeManager


class KToggle(QWidget):
    """
    Toggle switch.

        toggle = KToggle(checked=False)
        toggle.toggled.connect(lambda v: print(v))
    """

    toggled = pyqtSignal(bool)

    WIDTH = 48
    HEIGHT = 26
    KNOB_MARGIN = 3

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self._knob_x = float(self._knob_on_x() if checked else self._knob_off_x())

        self.setFixedSize(self.WIDTH, self.HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._anim = QPropertyAnimation(self, b"knobX")
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        self._tm = ThemeManager.instance()
        self._tm.changed.connect(self.update)

    # ── state ───────────────────────────────────────

    @property
    def checked(self) -> bool:
        return self._checked

    @checked.setter
    def checked(self, value: bool):
        if value != self._checked:
            self._checked = value
            self._animate()
            self.toggled.emit(value)

    # ── knob position property ──────────────────────

    def _knob_off_x(self) -> float:
        return float(self.KNOB_MARGIN)

    def _knob_on_x(self) -> float:
        knob_d = self.HEIGHT - 2 * self.KNOB_MARGIN
        return float(self.WIDTH - self.KNOB_MARGIN - knob_d)

    def _get_knob_x(self) -> float:
        return self._knob_x

    def _set_knob_x(self, v: float):
        self._knob_x = v
        self.update()

    knobX = pyqtProperty(float, _get_knob_x, _set_knob_x)

    def _animate(self):
        self._anim.stop()
        self._anim.setStartValue(self._knob_x)
        self._anim.setEndValue(
            self._knob_on_x() if self._checked else self._knob_off_x()
        )
        self._anim.start()

    # ── click ───────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.checked = not self._checked

    # ── paint ───────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self._tm

        # track
        track_rect = QRectF(0, 0, self.WIDTH, self.HEIGHT)
        radius = self.HEIGHT / 2

        if self._checked:
            track_color = QColor(t.fg)
        else:
            track_color = QColor(t.disabled)

        p.setBrush(track_color)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(track_rect, radius, radius)

        # knob
        knob_d = self.HEIGHT - 2 * self.KNOB_MARGIN
        knob_rect = QRectF(self._knob_x, self.KNOB_MARGIN, knob_d, knob_d)

        knob_color = QColor(t.bg)
        p.setBrush(knob_color)
        p.drawEllipse(knob_rect)

        p.end()