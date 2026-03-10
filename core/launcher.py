"""
Launcher window for selecting which app to run.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QApplication
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class LauncherWindow(QWidget):
    """Standalone launcher window."""

    app_selected = pyqtSignal(object)
    closed_without_selection = pyqtSignal()

    def __init__(self, manifests: list):
        super().__init__()

        self._manifests = manifests
        self._selected = False
        self._dragging = False
        self._drag_pos = None

        self.setWindowTitle("Kislinka Core")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
        )
        self.setFixedSize(500, 400)

        bg = "#000000"
        fg = "#FFFFFF"
        fg_dim = "#666666"
        border = "#2A2A2A"
        btn_bg = "#FFFFFF"
        btn_fg = "#000000"

        self.setStyleSheet(f"QWidget {{ background: {bg}; color: {fg}; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)

        inner = QWidget()
        inner.setStyleSheet(f"background: {bg}; border: 1px solid {border};")
        inner_lay = QVBoxLayout(inner)
        inner_lay.setContentsMargins(30, 30, 30, 30)
        inner_lay.setSpacing(16)

        title = QLabel("Kislinka Launcher")
        title.setFont(QFont("Mitr", 32))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {fg}; background: transparent; border: none;")
        inner_lay.addWidget(title)

        sub = QLabel("Select an application")
        sub.setFont(QFont("Roboto", 12, QFont.Weight.Bold))
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(f"color: {fg_dim}; background: transparent; border: none;")
        inner_lay.addWidget(sub)

        inner_lay.addSpacing(10)

        for m in manifests:
            btn = QPushButton(f"{m.display_name}  v{m.version}")
            btn.setFixedHeight(48)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFont(QFont("Roboto", 13, QFont.Weight.Bold))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {btn_bg};
                    color: {btn_fg};
                    border: none;
                    border-radius: 8px;
                }}
                QPushButton:hover {{
                    background: #E5E5E5;
                }}
                QPushButton:pressed {{
                    background: #CCCCCC;
                }}
            """)

            def make_handler(manifest):
                def handler():
                    self._selected = True
                    self.app_selected.emit(manifest)
                return handler

            btn.clicked.connect(make_handler(m))
            inner_lay.addWidget(btn)

        inner_lay.addStretch()

        footer = QLabel(f"{len(manifests)} application(s) found")
        footer.setFont(QFont("Roboto", 10, QFont.Weight.Bold))
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(f"color: {fg_dim}; background: transparent; border: none;")
        inner_lay.addWidget(footer)

        layout.addWidget(inner)

        self._center_on_screen()

    def _center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.geometry()
            x = (geo.width() - self.width()) // 2
            y = (geo.height() - self.height()) // 2
            self.move(x, y)

    def closeEvent(self, event):
        if not self._selected:
            self.closed_without_selection.emit()
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._dragging = False