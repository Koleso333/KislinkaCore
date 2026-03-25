from __future__ import annotations

from PyQt6.QtWidgets import QCheckBox
from PyQt6.QtCore import Qt, QRectF, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QPen

from core.animation import KAnimator, KEasing
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

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setStyleSheet("background: transparent;")
        self.setMinimumHeight(max(self._box + 6, 24))

        # animation state: 0.0 = unchecked, 1.0 = checked
        self._anim_val: float = 1.0 if checked else 0.0
        self._anim = None

        self._tm = ThemeManager.instance()
        self._apply_theme()
        self._tm.changed.connect(self._apply_theme)

        # set checked AFTER anim_val so initial paint is correct
        self.setChecked(checked)
        self.toggled.connect(self._on_toggled)

    # ── animated value property ─────────────────────

    def _get_anim_val(self) -> float:
        return self._anim_val

    def _set_anim_val(self, v: float) -> None:
        self._anim_val = v
        self.update()

    animVal = pyqtProperty(float, _get_anim_val, _set_anim_val)

    def _on_toggled(self, checked: bool) -> None:
        target = 1.0 if checked else 0.0
        if self._anim is not None:
            self._anim.stop()
        self._anim = KAnimator.start(
            self, b"animVal",
            start=self._anim_val, end=target,
            duration=180, easing=KEasing.OUT_CUBIC,
            parent=self,
        )

    def _apply_theme(self) -> None:
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        t = self._tm
        enabled = self.isEnabled()
        checked = self.isChecked()
        v = self._anim_val  # 0.0 → 1.0

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
        fg_color = QColor(t.fg if enabled else t.disabled)

        # interpolate fill: bg_alt → fg
        fill_color = QColor(
            int(bg_color.red()   + (fg_color.red()   - bg_color.red())   * v),
            int(bg_color.green() + (fg_color.green() - bg_color.green()) * v),
            int(bg_color.blue()  + (fg_color.blue()  - bg_color.blue())  * v),
        )

        # box
        p.setPen(QPen(border_color, 1.5))
        p.setBrush(fill_color)
        p.drawRoundedRect(box_rect, radius, radius)

        # icon — cross-fade between close (unchecked) and check (checked)
        icon_size = max(10, int(box * 0.70))
        icon_x = box_rect.center().x() - icon_size / 2
        icon_y = box_rect.center().y() - icon_size / 2
        icon_target = QRectF(icon_x, icon_y, icon_size, icon_size)

        # unchecked icon (cross) — fades out
        if v < 1.0:
            ico_color = t.fg if enabled else t.fg_dim
            ico = load_svg_icon("close", color=ico_color, size=icon_size, auto_invert=False)
            pm = ico.pixmap(icon_size, icon_size)
            p.setOpacity(1.0 - v)
            p.drawPixmap(icon_target.toRect(), pm)

        # checked icon (checkmark) — fades in
        if v > 0.0:
            ico_color = t.bg if enabled else t.bg_alt
            ico = load_svg_icon("check", color=ico_color, size=icon_size, auto_invert=False)
            pm = ico.pixmap(icon_size, icon_size)
            # scale from center for a pop effect
            scale = 0.5 + 0.5 * v
            p.setOpacity(v)
            p.save()
            cx = icon_target.center().x()
            cy = icon_target.center().y()
            p.translate(cx, cy)
            p.scale(scale, scale)
            p.translate(-cx, -cy)
            p.drawPixmap(icon_target.toRect(), pm)
            p.restore()

        p.setOpacity(1.0)

        # text
        p.setPen(text_color)
        p.setFont(self.font())
        p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text())

        p.end()
