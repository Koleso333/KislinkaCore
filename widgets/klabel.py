"""
KLabel — themed label with auto font selection.
"""

from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt

from core.theme import ThemeManager
from core.fonts import Fonts


class KLabel(QLabel):

    _PRESETS = {
        "heading": {"font": "heading", "size": 28, "color": "fg"},
        "body":    {"font": "body",    "size": 14, "color": "fg"},
        "dim":     {"font": "body",    "size": 13, "color": "fg_dim"},
        "small":   {"font": "body",    "size": 11, "color": "fg_dim"},
    }

    def __init__(
        self,
        text: str = "",
        *,
        style: str = "body",
        font_size: int | None = None,
        align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft,
        parent=None,
    ):
        super().__init__(text, parent)

        preset = self._PRESETS.get(style, self._PRESETS["body"])
        self._color_key = preset["color"]
        size = font_size or preset["size"]

        if preset["font"] == "heading":
            self.setFont(Fonts.heading(size))
        else:
            self.setFont(Fonts.body(size))

        self.setAlignment(align)

        self._tm = ThemeManager.instance()
        self._apply_theme()
        self._tm.changed.connect(self._apply_theme)

    def _apply_theme(self):
        color = getattr(self._tm, self._color_key)
        self.setStyleSheet(f"color: {color}; background: transparent;")