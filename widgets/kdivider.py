"""
KDivider — themed horizontal or vertical separator line.

    # Horizontal divider (default)
    divider = KDivider()

    # Vertical divider
    divider = KDivider(direction="vertical")

    # Custom thickness
    divider = KDivider(thickness=2)

    # Custom color key ("border", "fg_dim", "hover", "disabled")
    divider = KDivider(color_key="hover")
"""

from PyQt6.QtWidgets import QWidget

from core.theme import ThemeManager


class KDivider(QWidget):
    """
    Themed separator line.

    Automatically uses theme border color and reacts to theme changes.
    """

    def __init__(
        self,
        direction: str = "horizontal",
        *,
        thickness: int = 1,
        color_key: str = "border",
        margins: tuple[int, int, int, int] = (0, 0, 0, 0),
        parent=None,
    ):
        """
        direction: "horizontal" or "vertical"
        thickness: line thickness in pixels
        color_key: theme color property name ("border", "fg_dim", "hover", "disabled")
        margins: surrounding margins (left, top, right, bottom)
        """
        super().__init__(parent)
        self._color_key = color_key
        self._direction = direction

        if direction == "vertical":
            self.setFixedWidth(thickness)
        else:
            self.setFixedHeight(thickness)

        self.setContentsMargins(*margins)

        self._tm = ThemeManager.instance()
        self._apply_theme()
        self._tm.changed.connect(self._apply_theme)

    def _apply_theme(self):
        color = getattr(self._tm, self._color_key, self._tm.border)
        self.setStyleSheet(f"background: {color};")

    def set_color_key(self, key: str):
        """Change color source at runtime."""
        self._color_key = key
        self._apply_theme()
