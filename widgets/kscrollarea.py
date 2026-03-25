"""
KScrollArea — themed scrollable area with smooth animated scrolling.

    scroll = KScrollArea()
    scroll.set_content(my_widget)
"""

from PyQt6.QtWidgets import QScrollArea, QWidget, QScrollBar
from PyQt6.QtCore import Qt, pyqtProperty
from PyQt6.QtGui import QWheelEvent

from core.animation import KAnimator, KEasing
from core.theme import ThemeManager


class _SmoothScrollBar(QScrollBar):
    """QScrollBar that animates to target value on wheel events."""

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self._target: float = 0.0
        self._anim = None

    # animated value property
    def _get_smooth(self) -> float:
        return float(self.value())

    def _set_smooth(self, v: float) -> None:
        self.setValue(int(round(v)))

    smoothVal = pyqtProperty(float, _get_smooth, _set_smooth)

    def scroll_by(self, delta: int) -> None:
        """Animate scroll by *delta* pixels."""
        self._target = max(
            self.minimum(),
            min(self.maximum(), self._target + delta),
        )
        if self._anim is not None:
            self._anim.stop()
        self._anim = KAnimator.start(
            self, b"smoothVal",
            start=float(self.value()), end=self._target,
            duration=280, easing=KEasing.OUT_EXPO,
            parent=self,
        )

    def sync_target(self) -> None:
        """Sync target with actual value (e.g. after drag)."""
        self._target = float(self.value())


class KScrollArea(QScrollArea):
    """
    Themed scroll area with smooth animated scrolling.

    Features:
        - Auto-themed background (matches current theme)
        - Smooth animated wheel scrolling (ease-out expo)
        - Horizontal scroll disabled by default
        - Reacts to theme changes automatically
    """

    SCROLL_STEP = 80  # pixels per wheel notch

    def __init__(
        self,
        *,
        horizontal: bool = False,
        vertical: bool = True,
        parent=None,
    ):
        super().__init__(parent)

        self.setWidgetResizable(True)

        # Install smooth vertical scrollbar
        self._smooth_v = _SmoothScrollBar(Qt.Orientation.Vertical, self)
        self.setVerticalScrollBar(self._smooth_v)

        if not horizontal:
            self.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
            )
        if not vertical:
            self.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff,
            )

        self._tm = ThemeManager.instance()
        self._apply_theme()
        self._tm.changed.connect(self._apply_theme)

    def set_content(self, widget: QWidget):
        """Set the scrollable content widget."""
        self.setWidget(widget)

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Intercept wheel and animate scroll smoothly."""
        angle = event.angleDelta().y()
        if angle == 0:
            super().wheelEvent(event)
            return

        # Sync target in case user dragged the scrollbar manually
        self._smooth_v.sync_target()

        # angleDelta is typically ±120 per notch
        pixels = -int(angle / 120.0 * self.SCROLL_STEP)
        self._smooth_v.scroll_by(pixels)
        event.accept()

    def _apply_theme(self):
        t = self._tm
        self.setStyleSheet(f"""
            QScrollArea {{
                background: {t.bg};
                border: none;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 2px 0;
            }}
            QScrollBar::handle:vertical {{
                background: {t.scrollbar};
                min-height: 30px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {t.fg_dim};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
        """)
