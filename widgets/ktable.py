from __future__ import annotations

from PyQt6.QtWidgets import QTableWidget, QHeaderView

from core.theme import ThemeManager
from core.fonts import Fonts


class KTable(QTableWidget):
    def __init__(
        self,
        *,
        rows: int = 0,
        columns: int = 0,
        headers: list[str] | None = None,
        font_size: int = 13,
        parent=None,
    ):
        super().__init__(rows, columns, parent)

        self.setFont(Fonts.body(font_size))

        self.setShowGrid(False)
        self.setAlternatingRowColors(False)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        if headers is not None:
            self.set_headers(headers)

        self._tm = ThemeManager.instance()
        self._apply_theme()
        self._tm.changed.connect(self._apply_theme)

    def set_headers(self, headers: list[str]) -> None:
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels([str(h) for h in headers])

    def _apply_theme(self) -> None:
        t = self._tm
        self.setStyleSheet(
            f"""
            QTableWidget {{
                background: {t.bg_alt};
                color: {t.fg};
                border: 1.5px solid {t.border};
                border-radius: 6px;
                gridline-color: transparent;
                outline: 0;
            }}
            QTableWidget::item {{
                padding: 8px 10px;
                border: none;
            }}
            QTableWidget::item:selected:enabled {{
                background: {t.fg};
                color: {t.bg};
            }}
            QHeaderView::section {{
                background: {t.bg_alt};
                color: {t.fg_dim};
                border: none;
                border-bottom: 1px solid {t.border};
                padding: 8px 10px;
                font-weight: 700;
            }}
            QTableWidget:disabled {{
                color: {t.fg_dim};
                border: 1.5px solid {t.disabled};
            }}
            """
        )
