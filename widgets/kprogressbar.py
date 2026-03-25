from __future__ import annotations

from PyQt6.QtWidgets import QProgressBar
from PyQt6.QtCore import Qt, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QPen

from core.animation import KAnimator, KEasing
from core.theme import ThemeManager
from core.fonts import Fonts


class KProgressBar(QProgressBar):
    def __init__(
        self,
        *,
        value: int = 0,
        minimum: int = 0,
        maximum: int = 100,
        height: int = 12,
        show_text: bool = False,
        font_size: int = 12,
        parent=None,
    ):
        super().__init__(parent)

        self.setRange(minimum, maximum)
        self.setFixedHeight(height)
        self.setTextVisible(show_text)
        self.setFont(Fonts.body(font_size))

        # animated ratio (0.0 → 1.0)
        span = max(1, maximum - minimum)
        self._display_ratio: float = max(0.0, min(1.0, (value - minimum) / span))
        self._ratio_anim = None

        self._tm = ThemeManager.instance()
        self._apply_theme()
        self._tm.changed.connect(self._apply_theme)

        # set value after everything is initialised
        self.setValue(value)

    # ── animated ratio property ─────────────────────

    def _get_display_ratio(self) -> float:
        return self._display_ratio

    def _set_display_ratio(self, v: float) -> None:
        self._display_ratio = v
        self.update()

    displayRatio = pyqtProperty(float, _get_display_ratio, _set_display_ratio)

    def setValue(self, value: int) -> None:  # noqa: N802
        super().setValue(value)
        mn = self.minimum()
        mx = self.maximum()
        span = max(1, mx - mn)
        target = max(0.0, min(1.0, (value - mn) / span))

        if self._ratio_anim is not None:
            self._ratio_anim.stop()
        self._ratio_anim = KAnimator.start(
            self, b"displayRatio",
            start=self._display_ratio, end=target,
            duration=260, easing=KEasing.OUT_CUBIC,
            parent=self,
        )

    def _apply_theme(self) -> None:
        # We paint manually to guarantee rounded chunk and correct text contrast.
        self.setStyleSheet("")
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        t = self._tm
        enabled = self.isEnabled()

        bg = QColor(t.bg_alt)
        border = QColor(t.border if enabled else t.disabled)
        fill = QColor(t.fg if enabled else t.disabled)

        # text color outside the fill
        text_out = QColor(t.fg if enabled else t.fg_dim)
        # text color on top of the fill (invert)
        text_in = QColor(t.bg if enabled else t.bg_alt)

        w = self.width()
        h = self.height()
        r = max(2, int(h / 2))

        rect = self.rect().adjusted(1, 1, -1, -1)

        # background
        p.setPen(QPen(border, 1))
        p.setBrush(bg)
        p.drawRoundedRect(rect, r, r)

        # fill (clipped to rounded rect to keep corners smooth)
        ratio = self._display_ratio
        fill_w = int(rect.width() * ratio)

        if fill_w > 0:
            fill_rect = rect.adjusted(0, 0, -(rect.width() - fill_w), 0)
            p.save()
            p.setClipRect(fill_rect)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(fill)
            p.drawRoundedRect(rect, r, r)
            p.restore()

        # centered text with dynamic contrast (draw twice with different clip)
        if self.isTextVisible():
            txt = self.text()
            p.setFont(self.font())

            p.setPen(text_out)
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, txt)

            if fill_w > 0:
                fill_rect = rect.adjusted(0, 0, -(rect.width() - fill_w), 0)
                p.save()
                p.setClipRect(fill_rect)
                p.setPen(text_in)
                p.drawText(rect, Qt.AlignmentFlag.AlignCenter, txt)
                p.restore()

        p.end()
