from __future__ import annotations

from PyQt6.QtWidgets import QListWidget

from core.theme import ThemeManager
from core.fonts import Fonts


class KList(QListWidget):
    def __init__(
        self,
        items: list[str] | None = None,
        *,
        font_size: int = 13,
        parent=None,
    ):
        super().__init__(parent)

        self.setFont(Fonts.body(font_size))
        if items:
            self.set_items(items)

        self._tm = ThemeManager.instance()
        self._apply_theme()
        self._tm.changed.connect(self._apply_theme)

    def set_items(self, items: list[str]) -> None:
        self.clear()
        for it in items:
            self.addItem(str(it))

    def _apply_theme(self) -> None:
        t = self._tm
        self.setStyleSheet(
            f"""
            QListWidget {{
                background: {t.bg_alt};
                color: {t.fg};
                border: 1.5px solid {t.border};
                border-radius: 6px;
                padding: 6px;
                outline: 0;
            }}
            QListWidget:disabled {{
                color: {t.fg_dim};
                border: 1.5px solid {t.disabled};
            }}
            QListWidget::item {{
                padding: 8px 10px;
                border-radius: 6px;
            }}
            QListWidget::item:hover:enabled {{
                background: {t.hover};
            }}
            QListWidget::item:selected:enabled {{
                background: {t.fg};
                color: {t.bg};
            }}
            """
        )
