"""
KPanel — themed container widget.

Replaces manual QWidget + setStyleSheet patterns.
Auto-themes background, border, border-radius.

    # Default: theme bg
    panel = KPanel()

    # Elevated surface (bg_alt)
    panel = KPanel(variant="alt")

    # With border
    panel = KPanel(variant="alt", border=True, radius=8)

    # Fixed width sidebar
    sidebar = KPanel(variant="alt", fixed_width=320)

    # Add content
    panel.add(widget)
    panel.add(widget, stretch=1)
    panel.add_spacing(12)
    panel.add_stretch()

    # Horizontal panel
    toolbar = KPanel(direction="horizontal", spacing=8)
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt

from core.theme import ThemeManager


class KPanel(QWidget):
    """
    Themed container widget.

    Variants:
        "default" — theme bg
        "alt"     — theme bg_alt (elevated surface)
        "custom"  — custom_bg color

    Features:
        - Auto-themed background, border, radius
        - Built-in layout (vertical or horizontal)
        - Fluent .add() API
        - Reacts to theme changes automatically
    """

    def __init__(
        self,
        variant: str = "default",
        *,
        direction: str = "vertical",
        spacing: int = 0,
        margins: tuple[int, int, int, int] = (0, 0, 0, 0),
        border: bool = False,
        radius: int = 0,
        fixed_width: int = 0,
        fixed_height: int = 0,
        custom_bg: str = "",
        parent=None,
    ):
        """
        variant: "default" (bg), "alt" (bg_alt), "custom" (uses custom_bg)
        direction: "vertical" or "horizontal"
        spacing: gap between children
        margins: (left, top, right, bottom)
        border: show themed border
        radius: corner radius
        fixed_width / fixed_height: constrain size
        custom_bg: hex color (only with variant="custom")
        """
        super().__init__(parent)
        self._variant = variant
        self._border = border
        self._radius = radius
        self._custom_bg = custom_bg

        # unique objectName prevents QSS cascading to children
        self._uid = f"_kp_{id(self)}"
        self.setObjectName(self._uid)

        if fixed_width > 0:
            self.setFixedWidth(fixed_width)
        if fixed_height > 0:
            self.setFixedHeight(fixed_height)

        if direction == "horizontal":
            self._layout = QHBoxLayout(self)
        else:
            self._layout = QVBoxLayout(self)

        self._layout.setContentsMargins(*margins)
        self._layout.setSpacing(spacing)

        self._tm = ThemeManager.instance()
        self._apply_theme()
        self._tm.changed.connect(self._apply_theme)

    # ── content API ─────────────────────────────────

    def add(self, widget: QWidget, stretch: int = 0, align: str = "") -> "KPanel":
        """Add widget to panel. Returns self for chaining."""
        a = self._parse_align(align)
        if a is not None:
            self._layout.addWidget(widget, stretch, a)
        else:
            self._layout.addWidget(widget, stretch)
        return self

    def add_layout(self, layout) -> "KPanel":
        self._layout.addLayout(layout)
        return self

    def add_stretch(self, factor: int = 1) -> "KPanel":
        self._layout.addStretch(factor)
        return self

    def add_spacing(self, size: int) -> "KPanel":
        self._layout.addSpacing(size)
        return self

    @property
    def layout_(self):
        """Access underlying layout."""
        return self._layout

    # ── theme ───────────────────────────────────────

    def _get_bg(self) -> str:
        if self._variant == "alt":
            return self._tm.bg_alt
        elif self._variant == "custom" and self._custom_bg:
            return self._custom_bg
        return self._tm.bg

    def _apply_theme(self):
        bg = self._get_bg()
        parts = [f"background: {bg};"]

        if self._border:
            parts.append(f"border: 1px solid {self._tm.border};")
        else:
            parts.append("border: none;")

        if self._radius > 0:
            parts.append(f"border-radius: {self._radius}px;")

        self.setStyleSheet(f"#{self._uid} {{ {' '.join(parts)} }}")

    def set_variant(self, variant: str):
        """Change variant at runtime."""
        self._variant = variant
        self._apply_theme()

    def set_custom_bg(self, color: str):
        """Set custom background color."""
        self._custom_bg = color
        self._variant = "custom"
        self._apply_theme()

    @staticmethod
    def _parse_align(align: str):
        if not align:
            return None
        _FLAGS = {
            "left": Qt.AlignmentFlag.AlignLeft,
            "right": Qt.AlignmentFlag.AlignRight,
            "center": Qt.AlignmentFlag.AlignCenter,
            "hcenter": Qt.AlignmentFlag.AlignHCenter,
            "top": Qt.AlignmentFlag.AlignTop,
            "bottom": Qt.AlignmentFlag.AlignBottom,
            "vcenter": Qt.AlignmentFlag.AlignVCenter,
        }
        result = None
        for part in align.replace("|", " ").replace(",", " ").split():
            part = part.strip().lower()
            if part in _FLAGS:
                if result is None:
                    result = _FLAGS[part]
                else:
                    result |= _FLAGS[part]
        return result
