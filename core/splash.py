"""
Splash overlay shown inside the main window during app loading.
Covers the ENTIRE window including titlebar.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QPainter, QFont, QColor

from core.hooks import HookManager


class SplashOverlay(QWidget):
    """
    Overlay widget shown on top of the entire window.
    """

    def __init__(self, parent_window: QWidget, app_name: str = "Loading..."):
        # parent is the WINDOW itself, not body
        super().__init__(parent_window)
        hooks = HookManager.instance()
        self._app_name = hooks.filter("splash_text", app_name)
        self._scale = 1.0
        self._opacity = 1.0
        self._finished = False
        self._parent_window = parent_window

        # cover entire window
        self.setGeometry(0, 0, parent_window.width(), parent_window.height())
        self.raise_()
        self.show()

    def resizeEvent(self, event):
        """Stay covering parent if resized."""
        super().resizeEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(self._opacity)

        w = self.width()
        h = self.height()

        # center scale
        cx = w / 2
        cy = h / 2
        p.translate(cx, cy)
        p.scale(self._scale, self._scale)
        p.translate(-cx, -cy)

        # background — fill everything
        p.fillRect(0, 0, w, h, QColor("#000000"))

        # app name centered
        p.setPen(QColor("#FFFFFF"))
        font = QFont("Mitr", 42)
        p.setFont(font)
        p.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter, self._app_name)

        p.end()

    # ── animation properties ────────────────────────

    def _get_scale(self) -> float:
        return self._scale

    def _set_scale(self, v: float):
        self._scale = v
        self.update()

    def _get_opacity(self) -> float:
        return self._opacity

    def _set_opacity(self, v: float):
        self._opacity = v
        self.update()

    splashScale = pyqtProperty(float, _get_scale, _set_scale)
    splashOpacity = pyqtProperty(float, _get_opacity, _set_opacity)

    # ── finish ──────────────────────────────────────

    def finish(self, callback=None):
        """Animate out: scale up + fade out, then remove."""
        if self._finished:
            if callback:
                callback()
            return
        self._finished = True

        self._scale_anim = QPropertyAnimation(self, b"splashScale")
        self._scale_anim.setDuration(400)
        self._scale_anim.setStartValue(1.0)
        self._scale_anim.setEndValue(1.15)
        self._scale_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._opacity_anim = QPropertyAnimation(self, b"splashOpacity")
        self._opacity_anim.setDuration(400)
        self._opacity_anim.setStartValue(1.0)
        self._opacity_anim.setEndValue(0.0)
        self._opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        def on_done():
            self.hide()
            self.setParent(None)
            self.deleteLater()
            if callback:
                callback()

        self._opacity_anim.finished.connect(on_done)

        self._scale_anim.start()
        self._opacity_anim.start()

    def set_text(self, text: str):
        self._app_name = text
        self.update()