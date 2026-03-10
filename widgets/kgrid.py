"""
Smart layout containers: KRow, KColumn, KGrid.

Fluent API — chain .add() calls to build layouts easily.

    from widgets.kgrid import KRow, KColumn, KGrid

    # horizontal row
    row = KRow(spacing=12)
    row.add(KButton("A")).add(KButton("B")).add_stretch()

    # vertical column
    col = KColumn(spacing=8, margins=(20, 10, 20, 10))
    col.add(KLabel("Title", style="heading"))
    col.add(text_field, stretch=1)
    col.add_stretch()

    # auto-placement grid (fills left-to-right, wraps rows)
    grid = KGrid(columns=3, spacing=12)
    for widget in widgets:
        grid.add(widget)

    # manual placement
    grid = KGrid(columns=4)
    grid.place(wide_widget, row=0, col=0, colspan=2)
    grid.place(tall_widget, row=0, col=2, rowspan=2)
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QGridLayout
from PyQt6.QtCore import Qt


def _parse_align(align: str):
    """Parse alignment string like 'center', 'left|vcenter', 'top,right'."""
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


class KRow(QWidget):
    """
    Horizontal layout container with fluent API.

        row = KRow(spacing=12, align="vcenter")
        row.add(label).add(button).add_stretch()
    """

    def __init__(
        self,
        spacing: int = 8,
        margins: tuple[int, int, int, int] = (0, 0, 0, 0),
        align: str = "",
        parent=None,
    ):
        """
        spacing: gap between children
        margins: (left, top, right, bottom)
        align: layout alignment ('left', 'center', 'vcenter', etc.)
        """
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(*margins)
        self._layout.setSpacing(spacing)
        self.setStyleSheet("background: transparent;")

        a = _parse_align(align)
        if a is not None:
            self._layout.setAlignment(a)

    def add(self, widget: QWidget, stretch: int = 0, align: str = "") -> "KRow":
        """Add widget. Returns self for chaining."""
        a = _parse_align(align)
        if a is not None:
            self._layout.addWidget(widget, stretch, a)
        else:
            self._layout.addWidget(widget, stretch)
        return self

    def add_stretch(self, factor: int = 1) -> "KRow":
        self._layout.addStretch(factor)
        return self

    def add_spacing(self, size: int) -> "KRow":
        self._layout.addSpacing(size)
        return self

    def add_layout(self, layout) -> "KRow":
        self._layout.addLayout(layout)
        return self

    @property
    def layout_(self) -> QHBoxLayout:
        """Access underlying QHBoxLayout."""
        return self._layout


class KColumn(QWidget):
    """
    Vertical layout container with fluent API.

        col = KColumn(spacing=12, margins=(20, 10, 20, 10))
        col.add(KLabel("Title", style="heading"))
        col.add(content, stretch=1)
        col.add_stretch()
    """

    def __init__(
        self,
        spacing: int = 8,
        margins: tuple[int, int, int, int] = (0, 0, 0, 0),
        align: str = "",
        parent=None,
    ):
        """
        spacing: gap between children
        margins: (left, top, right, bottom)
        align: layout alignment ('center', 'top', etc.)
        """
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(*margins)
        self._layout.setSpacing(spacing)
        self.setStyleSheet("background: transparent;")

        a = _parse_align(align)
        if a is not None:
            self._layout.setAlignment(a)

    def add(self, widget: QWidget, stretch: int = 0, align: str = "") -> "KColumn":
        """Add widget. Returns self for chaining."""
        a = _parse_align(align)
        if a is not None:
            self._layout.addWidget(widget, stretch, a)
        else:
            self._layout.addWidget(widget, stretch)
        return self

    def add_stretch(self, factor: int = 1) -> "KColumn":
        self._layout.addStretch(factor)
        return self

    def add_spacing(self, size: int) -> "KColumn":
        self._layout.addSpacing(size)
        return self

    def add_layout(self, layout) -> "KColumn":
        self._layout.addLayout(layout)
        return self

    @property
    def layout_(self) -> QVBoxLayout:
        """Access underlying QVBoxLayout."""
        return self._layout


class KGrid(QWidget):
    """
    Grid layout container with auto-placement.

        # Auto-placement (fills left → right, wraps to next row)
        grid = KGrid(columns=3, spacing=12)
        grid.add(w1).add(w2).add(w3)   # row 0
        grid.add(w4).add(w5)            # row 1

        # Manual placement
        grid = KGrid(columns=4)
        grid.place(header, row=0, col=0, colspan=4)
        grid.place(sidebar, row=1, col=0, rowspan=2)
        grid.place(content, row=1, col=1, colspan=3)

        # Column stretch (make cols expand equally)
        grid = KGrid(columns=3, equal_columns=True)
    """

    def __init__(
        self,
        columns: int = 2,
        spacing: int = 8,
        row_spacing: int | None = None,
        col_spacing: int | None = None,
        margins: tuple[int, int, int, int] = (0, 0, 0, 0),
        equal_columns: bool = False,
        parent=None,
    ):
        """
        columns: number of columns for auto-placement
        spacing: uniform gap (overridden by row_spacing / col_spacing)
        row_spacing / col_spacing: independent spacing
        margins: (left, top, right, bottom)
        equal_columns: if True, all columns have equal stretch
        """
        super().__init__(parent)
        self._columns = max(1, columns)
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(*margins)
        self._layout.setHorizontalSpacing(
            col_spacing if col_spacing is not None else spacing,
        )
        self._layout.setVerticalSpacing(
            row_spacing if row_spacing is not None else spacing,
        )
        self.setStyleSheet("background: transparent;")

        self._next_row = 0
        self._next_col = 0

        if equal_columns:
            for c in range(self._columns):
                self._layout.setColumnStretch(c, 1)

    def add(
        self,
        widget: QWidget,
        rowspan: int = 1,
        colspan: int = 1,
        align: str = "",
    ) -> "KGrid":
        """
        Auto-place widget in the next available cell.
        Returns self for chaining.
        """
        row = self._next_row
        col = self._next_col

        a = _parse_align(align)
        if a is not None:
            self._layout.addWidget(widget, row, col, rowspan, colspan, a)
        else:
            self._layout.addWidget(widget, row, col, rowspan, colspan)

        # advance cursor
        self._next_col += colspan
        while self._next_col >= self._columns:
            self._next_col -= self._columns
            self._next_row += 1

        return self

    def place(
        self,
        widget: QWidget,
        row: int,
        col: int,
        rowspan: int = 1,
        colspan: int = 1,
        align: str = "",
    ) -> "KGrid":
        """Place widget at explicit grid position."""
        a = _parse_align(align)
        if a is not None:
            self._layout.addWidget(widget, row, col, rowspan, colspan, a)
        else:
            self._layout.addWidget(widget, row, col, rowspan, colspan)
        return self

    def skip(self, count: int = 1) -> "KGrid":
        """Skip N cells in auto-placement."""
        for _ in range(count):
            self._next_col += 1
            if self._next_col >= self._columns:
                self._next_col = 0
                self._next_row += 1
        return self

    def next_row(self) -> "KGrid":
        """Jump to the start of the next row."""
        if self._next_col > 0:
            self._next_col = 0
            self._next_row += 1
        return self

    def set_row_stretch(self, row: int, stretch: int) -> "KGrid":
        self._layout.setRowStretch(row, stretch)
        return self

    def set_col_stretch(self, col: int, stretch: int) -> "KGrid":
        self._layout.setColumnStretch(col, stretch)
        return self

    def set_min_col_width(self, col: int, width: int) -> "KGrid":
        self._layout.setColumnMinimumWidth(col, width)
        return self

    def set_min_row_height(self, row: int, height: int) -> "KGrid":
        self._layout.setRowMinimumHeight(row, height)
        return self

    @property
    def columns(self) -> int:
        return self._columns

    @property
    def layout_(self) -> QGridLayout:
        """Access underlying QGridLayout."""
        return self._layout
