"""
KTextField — styled text input.
"""

import weakref
from PyQt6.QtWidgets import QLineEdit, QTextEdit, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor

from core.theme import ThemeManager
from core.fonts import Fonts


def _is_alive(obj) -> bool:
    """Check if Qt object is still alive."""
    try:
        obj.objectName()
        return True
    except (RuntimeError, ReferenceError):
        return False


class _CursorBlinker:
    _instance = None

    def __init__(self):
        self._timer = QTimer()
        self._timer.setInterval(800)
        self._visible = True
        self._listeners: list[weakref.ref] = []
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, callback_owner):
        """Register owner object (must have _on_blink method)."""
        ref = weakref.ref(callback_owner)
        self._listeners.append(ref)

    def unregister(self, callback_owner):
        self._listeners = [
            r for r in self._listeners
            if r() is not None and r() is not callback_owner
        ]

    @property
    def visible(self) -> bool:
        return self._visible

    def _tick(self):
        self._visible = not self._visible
        # clean up dead refs and call alive ones
        alive = []
        for ref in self._listeners:
            obj = ref()
            if obj is not None and _is_alive(obj):
                alive.append(ref)
                try:
                    obj._on_blink(self._visible)
                except (RuntimeError, ReferenceError):
                    pass
        self._listeners = alive


class _KSingleLine(QLineEdit):
    def __init__(self, placeholder, font_size, parent=None):
        super().__init__(parent)
        self.setFont(Fonts.body(font_size))
        self.setPlaceholderText(placeholder)

        self._tm = ThemeManager.instance()
        self._blinker = _CursorBlinker.instance()
        self._cursor_visible = True

        self._apply_theme()
        self._tm.changed.connect(self._safe_apply_theme)
        self._blinker.register(self)

    def _on_blink(self, visible: bool):
        self._cursor_visible = visible
        self._safe_apply_theme()

    def _safe_apply_theme(self):
        if not _is_alive(self):
            return
        self._apply_theme()

    def _apply_theme(self):
        t = self._tm
        self.setStyleSheet(f"""
            QLineEdit {{
                background:    {t.bg_alt};
                color:         {t.fg};
                border:        1.5px solid {t.border};
                border-radius: 6px;
                padding:       8px 12px;
                selection-background-color: {t.fg};
                selection-color:            {t.bg};
            }}
        """)
        pal = self.palette()
        pal.setColor(pal.ColorRole.Text, QColor(t.fg))
        pal.setColor(pal.ColorRole.PlaceholderText, QColor(t.fg_dim))
        self.setPalette(pal)

    def __del__(self):
        try:
            self._blinker.unregister(self)
        except Exception:
            pass


class _KMultiLine(QTextEdit):
    text_changed = pyqtSignal()

    def __init__(self, placeholder, font_size, parent=None):
        super().__init__(parent)
        self.setFont(Fonts.body(font_size))
        self.setPlaceholderText(placeholder)
        self.setAcceptRichText(False)
        self.textChanged.connect(self.text_changed.emit)

        self._tm = ThemeManager.instance()
        self._blinker = _CursorBlinker.instance()
        self._cursor_visible = True

        self._apply_theme()
        self._tm.changed.connect(self._safe_apply_theme)
        self._blinker.register(self)

    def _on_blink(self, visible: bool):
        self._cursor_visible = visible
        self._safe_apply_theme()

    def _safe_apply_theme(self):
        if not _is_alive(self):
            return
        self._apply_theme()

    def _apply_theme(self):
        t = self._tm
        self.setStyleSheet(f"""
            QTextEdit {{
                background:    {t.bg_alt};
                color:         {t.fg};
                border:        1.5px solid {t.border};
                border-radius: 6px;
                padding:       8px 12px;
                selection-background-color: {t.fg};
                selection-color:            {t.bg};
            }}
        """)
        pal = self.palette()
        pal.setColor(pal.ColorRole.Text, QColor(t.fg))
        pal.setColor(pal.ColorRole.PlaceholderText, QColor(t.fg_dim))
        self.setPalette(pal)

    def plain_text(self) -> str:
        return self.toPlainText()

    def set_text(self, text: str):
        self.setPlainText(text)

    def __del__(self):
        try:
            self._blinker.unregister(self)
        except Exception:
            pass


class KTextField(QWidget):

    text_changed = pyqtSignal()

    def __init__(
        self,
        *,
        placeholder: str = "",
        multiline: bool = False,
        font_size: int = 14,
        max_length: int | None = None,
        fixed_height: int | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._multiline = multiline

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if multiline:
            self._inner = _KMultiLine(placeholder, font_size, self)
            self._inner.text_changed.connect(self.text_changed.emit)
        else:
            self._inner = _KSingleLine(placeholder, font_size, self)
            self._inner.textChanged.connect(self.text_changed.emit)
            if max_length is not None:
                self._inner.setMaxLength(max_length)

        if fixed_height is not None:
            self._inner.setFixedHeight(fixed_height)

        layout.addWidget(self._inner)

    @property
    def text(self) -> str:
        if self._multiline:
            return self._inner.plain_text()
        return self._inner.text()

    @text.setter
    def text(self, value: str):
        if self._multiline:
            self._inner.set_text(value)
        else:
            self._inner.setText(value)

    def clear(self):
        self._inner.clear()

    def set_read_only(self, readonly: bool):
        self._inner.setReadOnly(readonly)