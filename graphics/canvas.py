"""
KCanvas — custom drawing widget.

Subclass and override on_draw() to draw custom graphics.

Usage:
    class MyCanvas(KCanvas):
        def on_draw(self, painter: QPainter):
            Shapes.rect(painter, 10, 10, 100, 50, color="#FF0000")
            Shapes.circle(painter, 200, 100, 40, color="#00FF00")
            self.my_image.draw(painter, 50, 50)

    canvas = MyCanvas()
    canvas.set_fps(60)   # auto-refresh at 60 fps
    canvas.refresh()     # manual refresh
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor

from core.theme import ThemeManager


class KCanvas(QWidget):
    """
    Base canvas widget for custom drawing.

    Override on_draw(painter) to draw your content.
    Call refresh() to trigger repaint, or set_fps(n) for auto-refresh.
    """

    def __init__(self, parent=None, bg_color: str | None = None):
        """
        bg_color: background color (None = use theme bg)
        """
        super().__init__(parent)
        self._bg_color = bg_color
        self._fps = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)

        self._tm = ThemeManager.instance()
        self._tm.changed.connect(self.refresh)

        # enable mouse tracking for mouse move events
        self.setMouseTracking(True)

    # ── settings ────────────────────────────────────

    def set_fps(self, fps: int):
        """Set auto-refresh rate. 0 = manual refresh only."""
        self._fps = fps
        self._timer.stop()
        if fps > 0:
            self._timer.start(1000 // fps)

    def set_background(self, color: str | None):
        """Set background color (None = theme bg)."""
        self._bg_color = color
        self.refresh()

    def refresh(self):
        """Trigger repaint."""
        self.update()

    # ── override this ───────────────────────────────

    def on_draw(self, painter: QPainter):
        """Override to draw your content."""
        pass

    def on_mouse_press(self, x: int, y: int, button: Qt.MouseButton):
        """Override for mouse press handling."""
        pass

    def on_mouse_release(self, x: int, y: int, button: Qt.MouseButton):
        """Override for mouse release handling."""
        pass

    def on_mouse_move(self, x: int, y: int):
        """Override for mouse move handling."""
        pass

    def on_key_press(self, key: int, text: str):
        """Override for key press handling."""
        pass

    def on_key_release(self, key: int, text: str):
        """Override for key release handling."""
        pass

    # ── Qt events ───────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # background
        if self._bg_color:
            bg = QColor(self._bg_color)
        else:
            bg = QColor(self._tm.bg)
        painter.fillRect(self.rect(), bg)

        # user drawing
        self.on_draw(painter)

        painter.end()

    def mousePressEvent(self, event):
        self.on_mouse_press(int(event.position().x()), int(event.position().y()), event.button())

    def mouseReleaseEvent(self, event):
        self.on_mouse_release(int(event.position().x()), int(event.position().y()), event.button())

    def mouseMoveEvent(self, event):
        self.on_mouse_move(int(event.position().x()), int(event.position().y()))

    def keyPressEvent(self, event):
        self.on_key_press(event.key(), event.text())

    def keyReleaseEvent(self, event):
        self.on_key_release(event.key(), event.text())