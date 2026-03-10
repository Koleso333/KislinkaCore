"""
KScrollArea — themed scrollable area.

    scroll = KScrollArea()
    scroll.set_content(my_widget)

    # Or build content inline
    scroll = KScrollArea()
    content = KColumn(spacing=12, margins=(40, 20, 40, 20))
    content.add(label)
    content.add(button)
    scroll.set_content(content)

    # Disable horizontal scroll (default)
    scroll = KScrollArea(horizontal=False)
"""

from PyQt6.QtWidgets import QScrollArea, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt

from core.theme import ThemeManager


class KScrollArea(QScrollArea):
    """
    Themed scroll area.

    Features:
        - Auto-themed background (matches current theme)
        - Horizontal scroll disabled by default
        - Fluent API for setting content
        - Reacts to theme changes automatically
    """

    def __init__(
        self,
        *,
        horizontal: bool = False,
        vertical: bool = True,
        parent=None,
    ):
        """
        horizontal: enable horizontal scrollbar
        vertical: enable vertical scrollbar
        """
        super().__init__(parent)

        self.setWidgetResizable(True)

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

    def _apply_theme(self):
        self.setStyleSheet(
            f"QScrollArea {{ background: {self._tm.bg}; border: none; }}"
        )
