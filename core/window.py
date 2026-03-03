"""
Frameless fixed-size window.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QStyleOption, QStyle, QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter

from core.titlebar import TitleBar
from core.theme import ThemeManager


class KislinkaWindow(QWidget):
    """Main application window — frameless, fixed size."""

    DEFAULT_W = 900
    DEFAULT_H = 600

    def __init__(
        self,
        title: str = "KislinkaCore",
        width: int | None = None,
        height: int | None = None,
    ):
        super().__init__()

        w = width or self.DEFAULT_W
        h = height or self.DEFAULT_H

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
        )
        self.setFixedSize(w, h)

        self._should_quit = True  # can be set to False before close

        # layout
        root = QVBoxLayout(self)
        root.setContentsMargins(1, 1, 1, 1)
        root.setSpacing(0)

        inner = QWidget()
        inner.setObjectName("_KInner")
        inner_lay = QVBoxLayout(inner)
        inner_lay.setContentsMargins(0, 0, 0, 0)
        inner_lay.setSpacing(0)

        self._titlebar = TitleBar(title, self)
        inner_lay.addWidget(self._titlebar)

        self._sep = QWidget()
        self._sep.setFixedHeight(1)
        self._sep.setObjectName("_KSep")
        inner_lay.addWidget(self._sep)

        self._body = QWidget()
        self._body.setObjectName("_KBody")
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(0)
        inner_lay.addWidget(self._body, 1)

        root.addWidget(inner)

        self._tm = ThemeManager.instance()
        self._apply_theme()
        self._tm.changed.connect(self._apply_theme)

    @property
    def titlebar(self) -> TitleBar:
        return self._titlebar

    @property
    def body(self) -> QWidget:
        return self._body

    @property
    def body_layout(self) -> QVBoxLayout:
        return self._body_layout

    def set_content(self, widget: QWidget):
        while self._body_layout.count():
            item = self._body_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        self._body_layout.addWidget(widget, 1)

    def set_title(self, title: str):
        self._titlebar.set_title(title)

    def set_size(self, width: int, height: int):
        self.setFixedSize(width, height)

    def center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.geometry()
            x = (geo.width() - self.width()) // 2
            y = (geo.height() - self.height()) // 2
            self.move(x, y)

    def _apply_theme(self):
        t = self._tm
        self.setStyleSheet(f"KislinkaWindow {{ background: {t.scrollbar}; }}")
        self._body.setStyleSheet(f"#_KBody {{ background: {t.bg}; }}")
        self._sep.setStyleSheet(f"#_KSep  {{ background: {t.scrollbar}; }}")

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(
            QStyle.PrimitiveElement.PE_Widget, opt, p, self
        )

    def closeEvent(self, event):
        """When main window closes, quit ONLY if should_quit is True."""
        event.accept()
        if self._should_quit:
            QApplication.quit()