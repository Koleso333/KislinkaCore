"""
Custom title bar.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QPoint, QSize, pyqtSignal

from core.theme import ThemeManager
from core.fonts import Fonts
from widgets.kicon import load_svg_icon


class _TitleBarButton(QPushButton):
    def __init__(self, icon_name: str, icon_size: int = 16, parent=None):
        super().__init__(parent)
        self._icon_name = icon_name
        self._icon_size = icon_size
        self.setFixedSize(36, 36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setIconSize(QSize(icon_size, icon_size))
        self._apply_theme()
        ThemeManager.instance().changed.connect(self._apply_theme)

    def reconnect_theme(self):
        """Re-apply theme and reconnect signal."""
        tm = ThemeManager.instance()
        try:
            tm.changed.disconnect(self._apply_theme)
        except Exception:
            pass
        tm.changed.connect(self._apply_theme)
        self._apply_theme()

    def _apply_theme(self):
        tm = ThemeManager.instance()
        self.setIcon(load_svg_icon(self._icon_name, color=tm.fg, size=self._icon_size))
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 6px;
                padding: 0px;
            }}
            QPushButton:hover {{
                background: {tm.hover};
            }}
            QPushButton:pressed {{
                background: {tm.disabled};
            }}
        """)


class TitleBar(QWidget):
    """Draggable title bar with settings / minimize / close."""

    settings_clicked = pyqtSignal()

    HEIGHT = 42

    def __init__(self, title: str, parent_window: QWidget):
        super().__init__(parent_window)
        self._window = parent_window
        self._dragging = False
        self._drag_pos = QPoint()
        self._custom_buttons: list[QPushButton] = []
        self._custom_click_guard = None
        self.setFixedHeight(self.HEIGHT)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.setSpacing(2)

        # left: settings
        self._settings_btn = _TitleBarButton("settings", 18)
        self._settings_btn.clicked.connect(self.settings_clicked.emit)
        layout.addWidget(self._settings_btn)

        # left: custom app buttons container
        self._custom_left_layout = QHBoxLayout()
        self._custom_left_layout.setSpacing(2)
        layout.addLayout(self._custom_left_layout)

        layout.addStretch()

        # right: minimize, close
        self._minimize_btn = _TitleBarButton("minimize", 14)
        self._minimize_btn.clicked.connect(parent_window.showMinimized)
        layout.addWidget(self._minimize_btn)

        self._close_btn = _TitleBarButton("close", 14)
        self._close_btn.clicked.connect(parent_window.close)
        layout.addWidget(self._close_btn)

        # title overlay
        self._title = QLabel(title, self)
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title.setFont(Fonts.heading(13))
        self._title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._tm = ThemeManager.instance()
        self._apply_theme()
        self._tm.changed.connect(self._apply_theme)

    def set_custom_click_guard(self, guard):
        self._custom_click_guard = guard

    def set_title(self, text: str):
        self._title.setText(text)

    def add_custom_button(self, icon_name_or_path: str, callback, icon_size: int = 16) -> QPushButton:
        """Add a custom button to the titlebar (right of settings icon)."""
        btn = _TitleBarButton(icon_name_or_path, icon_size)

        def _on_click():
            try:
                if self._custom_click_guard and not self._custom_click_guard():
                    return
            except Exception:
                return
            callback()

        btn.clicked.connect(_on_click)
        self._custom_left_layout.addWidget(btn)
        self._custom_buttons.append(btn)
        return btn

    def set_custom_buttons_enabled(self, enabled: bool):
        for btn in self._custom_buttons:
            btn.setEnabled(enabled)

    def reconnect_theme(self):
        """Reconnect all theme signals after disconnect_all."""
        # remember custom buttons visibility state
        custom_visible = all(btn.isVisible() for btn in self._custom_buttons) if self._custom_buttons else True

        # reconnect own theme
        try:
            self._tm.changed.disconnect(self._apply_theme)
        except Exception:
            pass
        self._tm.changed.connect(self._apply_theme)
        self._apply_theme()

        # reconnect built-in buttons
        self._settings_btn.reconnect_theme()
        self._minimize_btn.reconnect_theme()
        self._close_btn.reconnect_theme()

        # reconnect custom buttons
        for btn in self._custom_buttons:
            if hasattr(btn, 'reconnect_theme'):
                btn.reconnect_theme()

        # restore custom buttons visibility state
        if not custom_visible:
            self.hide_custom_buttons()

    def clear_custom_buttons(self):
        """Remove all custom app buttons."""
        self._custom_buttons.clear()
        while self._custom_left_layout.count():
            item = self._custom_left_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

    def hide_custom_buttons(self):
        """Hide all custom buttons (when settings open)."""
        for btn in self._custom_buttons:
            btn.setVisible(False)
            btn.setEnabled(False)

    def show_custom_buttons(self):
        """Show all custom buttons (when settings close)."""
        for btn in self._custom_buttons:
            btn.setVisible(True)
            btn.setEnabled(True)

    def _apply_theme(self):
        self._title.setStyleSheet(f"color: {self._tm.fg}; background: transparent;")

    def resizeEvent(self, event):
        self._title.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self._window.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self._window.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._dragging = False
        event.accept()