"""
KSlider — themed horizontal slider with knob animation.

    slider = KSlider(min_value=0, max_value=100, value=50)
    slider.value_changed.connect(lambda v: print(v))

    # With step
    slider = KSlider(min_value=0, max_value=10, value=5, step=1)

    # Read / write
    slider.value = 75
    current = slider.value
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import (
    Qt, QRectF, QPointF, pyqtSignal, pyqtProperty,
    QPropertyAnimation, QEasingCurve,
)
from PyQt6.QtGui import QPainter, QColor, QPen

from core.theme import ThemeManager


class KSlider(QWidget):
    """
    Horizontal slider.

    Design:
      - Thin track (4px) with rounded caps
      - Filled portion from left to knob
      - Circular knob with inner dot
      - Knob grows on hover / drag
      - Fully theme-aware (B&W)
    """

    value_changed = pyqtSignal(float)

    TRACK_HEIGHT = 4
    KNOB_RADIUS = 9
    KNOB_RADIUS_ACTIVE = 11
    HEIGHT = 36

    def __init__(
        self,
        min_value: float = 0.0,
        max_value: float = 1.0,
        value: float = 0.0,
        *,
        step: float = 0.0,
        show_labels: bool = False,
        parent=None,
    ):
        """
        min_value / max_value: range
        value: initial value (clamped to range)
        step: snap increment (0 = continuous)
        show_labels: show min/max labels at edges
        """
        super().__init__(parent)
        self._min = min_value
        self._max = max(max_value, min_value)
        self._step = step
        self._show_labels = show_labels
        self._dragging = False
        self._hover = False
        self._knob_r = float(self.KNOB_RADIUS)

        # set value without emitting signal
        self._value = self._clamp(value)

        self.setFixedHeight(self.HEIGHT)
        self.setMinimumWidth(120)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setMouseTracking(True)

        # knob animation
        self._knob_anim = QPropertyAnimation(self, b"knobRadius")
        self._knob_anim.setDuration(120)
        self._knob_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._tm = ThemeManager.instance()
        self._tm.changed.connect(self.update)

    # ── value property ──────────────────────────────

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, v: float):
        v = self._clamp(v)
        if v != self._value:
            self._value = v
            self.update()
            self.value_changed.emit(v)

    @property
    def min_value(self) -> float:
        return self._min

    @min_value.setter
    def min_value(self, v: float):
        self._min = v
        self._max = max(self._max, v)
        self.value = self._value

    @property
    def max_value(self) -> float:
        return self._max

    @max_value.setter
    def max_value(self, v: float):
        self._max = v
        self._min = min(self._min, v)
        self.value = self._value

    @property
    def step(self) -> float:
        return self._step

    @step.setter
    def step(self, v: float):
        self._step = max(0.0, v)
        self.value = self._value

    # ── animated knob radius property ───────────────

    def _get_knob_r(self) -> float:
        return self._knob_r

    def _set_knob_r(self, v: float):
        self._knob_r = v
        self.update()

    knobRadius = pyqtProperty(float, _get_knob_r, _set_knob_r)

    # ── internal helpers ────────────────────────────

    def _clamp(self, v: float) -> float:
        v = max(self._min, min(self._max, v))
        if self._step > 0:
            v = round((v - self._min) / self._step) * self._step + self._min
            v = max(self._min, min(self._max, v))
        return v

    def _track_rect(self) -> tuple[float, float, float, float]:
        margin = self.KNOB_RADIUS_ACTIVE + 2
        x = margin
        y = self.height() / 2 - self.TRACK_HEIGHT / 2
        w = self.width() - 2 * margin
        return x, y, max(0, w), self.TRACK_HEIGHT

    def _ratio(self) -> float:
        span = self._max - self._min
        if span <= 0:
            return 0.0
        return (self._value - self._min) / span

    def _knob_center(self) -> QPointF:
        tx, ty, tw, th = self._track_rect()
        kx = tx + tw * self._ratio()
        ky = self.height() / 2
        return QPointF(kx, ky)

    def _value_from_x(self, x: float) -> float:
        tx, ty, tw, th = self._track_rect()
        if tw <= 0:
            return self._min
        ratio = max(0.0, min(1.0, (x - tx) / tw))
        return self._min + ratio * (self._max - self._min)

    def _animate_knob(self, target: float):
        self._knob_anim.stop()
        self._knob_anim.setStartValue(self._knob_r)
        self._knob_anim.setEndValue(target)
        self._knob_anim.start()

    # ── paint ───────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self._tm

        tx, ty, tw, th = self._track_rect()
        knob = self._knob_center()
        ratio = self._ratio()
        kr = self._knob_r

        # track background
        p.setBrush(QColor(t.disabled))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(tx, ty, tw, th), th / 2, th / 2)

        # filled portion
        if ratio > 0 and tw > 0:
            filled_w = tw * ratio
            p.setBrush(QColor(t.fg))
            p.drawRoundedRect(
                QRectF(tx, ty, filled_w, th), th / 2, th / 2,
            )

        # knob shadow
        shadow = QColor(0, 0, 0, 30)
        p.setBrush(shadow)
        p.drawEllipse(QPointF(knob.x(), knob.y() + 1), kr + 1, kr + 1)

        # knob body
        p.setBrush(QColor(t.fg))
        p.drawEllipse(knob, kr, kr)

        # knob inner dot
        inner_r = kr * 0.35
        p.setBrush(QColor(t.bg))
        p.drawEllipse(knob, inner_r, inner_r)

        # optional labels
        if self._show_labels:
            from core.fonts import Fonts
            p.setFont(Fonts.body(10))
            p.setPen(QColor(t.fg_dim))
            label_y = self.height() / 2 + kr + 12
            p.drawText(
                QPointF(tx, label_y),
                self._format_val(self._min),
            )
            max_text = self._format_val(self._max)
            fm = p.fontMetrics()
            max_w = fm.horizontalAdvance(max_text)
            p.drawText(
                QPointF(tx + tw - max_w, label_y),
                max_text,
            )

        p.end()

    def _format_val(self, v: float) -> str:
        if self._step > 0 and self._step == int(self._step):
            return str(int(v))
        return f"{v:.1f}"

    # ── mouse events ────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self.value = self._value_from_x(event.position().x())
            self._animate_knob(self.KNOB_RADIUS_ACTIVE)

    def mouseMoveEvent(self, event):
        if self._dragging:
            self.value = self._value_from_x(event.position().x())
        else:
            knob = self._knob_center()
            dx = event.position().x() - knob.x()
            dy = event.position().y() - knob.y()
            dist = (dx * dx + dy * dy) ** 0.5
            new_hover = dist <= self.KNOB_RADIUS_ACTIVE + 4
            if new_hover != self._hover:
                self._hover = new_hover
                self._animate_knob(
                    self.KNOB_RADIUS_ACTIVE if new_hover
                    else self.KNOB_RADIUS
                )

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            if not self._hover:
                self._animate_knob(self.KNOB_RADIUS)

    def leaveEvent(self, event):
        self._hover = False
        if not self._dragging:
            self._animate_knob(self.KNOB_RADIUS)

    def wheelEvent(self, event):
        """Scroll wheel support."""
        # Ignore wheel events to allow parent scrolling
        event.ignore()
