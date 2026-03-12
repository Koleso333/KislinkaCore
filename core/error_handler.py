"""
Global error handler.
Catches all unhandled exceptions including those in Qt slots.
"""

import sys
import traceback
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QPushButton,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


def _log(msg: str):
    print(f"[ErrorHandler] {msg}")


class ErrorWindow(QWidget):
    """Standalone error window in KislinkaCore style."""

    def __init__(self, error_type: str, error_msg: str, tb_text: str):
        super().__init__()

        self.setWindowTitle("KislinkaCore — Error")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
        )
        self.setFixedSize(600, 450)

        self._dragging = False
        self._drag_pos = None

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
        inner_lay.setContentsMargins(24, 20, 24, 24)
        inner_lay.setSpacing(16)

        title = QLabel("Error")
        title.setFont(QFont("Mitr", 28))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {fg}; background: transparent; border: none;")
        inner_lay.addWidget(title)

        type_label = QLabel(error_type)
        type_label.setFont(QFont("Roboto", 14, QFont.Weight.Bold))
        type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        type_label.setStyleSheet(f"color: {fg_dim}; background: transparent; border: none;")
        inner_lay.addWidget(type_label)

        msg_label = QLabel(error_msg)
        msg_label.setFont(QFont("Roboto", 12, QFont.Weight.Bold))
        msg_label.setWordWrap(True)
        msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_label.setStyleSheet(f"color: {fg}; background: transparent; border: none;")
        inner_lay.addWidget(msg_label)

        tb_edit = QTextEdit()
        tb_edit.setPlainText(tb_text)
        tb_edit.setReadOnly(True)
        tb_edit.setFont(QFont("Consolas", 10))
        tb_edit.setStyleSheet(f"""
            QTextEdit {{
                background: #0D0D0D;
                color: {fg_dim};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 8px;
            }}
        """)
        inner_lay.addWidget(tb_edit, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        btn_copy = QPushButton("Copy Error")
        btn_copy.setFixedHeight(44)
        btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy.setFont(QFont("Roboto", 12, QFont.Weight.Bold))
        btn_copy.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {fg};
                border: 1px solid {fg};
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background: #1A1A1A;
            }}
        """)
        btn_copy.clicked.connect(lambda: self._copy(tb_text))
        btn_row.addWidget(btn_copy)

        btn_close = QPushButton("Close")
        btn_close.setFixedHeight(44)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setFont(QFont("Roboto", 12, QFont.Weight.Bold))
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background: {btn_bg};
                color: {btn_fg};
                border: none;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background: #E0E0E0;
            }}
        """)
        btn_close.clicked.connect(self._on_close)
        btn_row.addWidget(btn_close)

        inner_lay.addLayout(btn_row)
        layout.addWidget(inner)

        self._center_on_screen()

    def _copy(self, text: str):
        cb = QApplication.clipboard()
        if cb:
            cb.setText(text)

    def _on_close(self):
        sys.exit(1)

    def _center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.geometry()
            x = (geo.width() - self.width()) // 2
            y = (geo.height() - self.height()) // 2
            self.move(x, y)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._dragging = False


class KislinkaQApplication(QApplication):
    """Custom QApplication that catches exceptions in Qt slots."""

    def notify(self, obj, event):
        try:
            return super().notify(obj, event)
        except Exception:
            ErrorHandler.handle_exception(*sys.exc_info())
            return False


class ErrorHandler:
    """Global exception handler."""

    _error_window: ErrorWindow | None = None
    _handling = False

    @classmethod
    def install(cls):
        """Install global exception handler."""
        sys.excepthook = cls.handle_exception
        _log("Error handler installed ✓")

    @classmethod
    def handle_exception(cls, exc_type, exc_value, exc_tb):
        """Handle uncaught exception."""
        if cls._handling:
            return
        cls._handling = True

        error_type = exc_type.__name__ if exc_type else "Unknown Error"
        error_msg = str(exc_value) if exc_value else "No details"
        tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))

        _log(f"Caught exception: {error_type}: {error_msg}")
        print(tb_text)

        # hook: components can react to errors (logging, reporting, etc.)
        try:
            from core.hooks import HookManager
            hooks = HookManager.instance()
            hooks.emit("on_error", error_type=error_type,
                       error_msg=error_msg, traceback=tb_text)
        except Exception:
            pass

        cls.show_error(error_type, error_msg, tb_text)

    @classmethod
    def show_error(cls, error_type: str, error_msg: str, tb_text: str = ""):
        """Show error window, hide all other windows without quitting."""
        app = QApplication.instance()
        if app:
            # hide all windows without triggering quit
            for widget in app.topLevelWidgets():
                if widget is not cls._error_window:
                    try:
                        # prevent closeEvent from calling quit
                        if hasattr(widget, '_should_quit'):
                            widget._should_quit = False
                        widget.hide()
                    except Exception:
                        pass

        cls._error_window = ErrorWindow(error_type, error_msg, tb_text)
        cls._error_window.show()
        cls._handling = False