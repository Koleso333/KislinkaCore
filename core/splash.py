"""
Splash overlay shown inside the main window during app loading.
Covers the ENTIRE window including titlebar.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtProperty
from PyQt6.QtGui import QPainter, QFont, QColor

from core.animation import KAnimator, KEasing
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

        self._scale_anim = KAnimator.animate(
            self, b"splashScale",
            start=1.0, end=1.15,
            duration=400, easing=KEasing.OUT_CUBIC,
            parent=self,
        )

        self._opacity_anim = KAnimator.animate(
            self, b"splashOpacity",
            start=1.0, end=0.0,
            duration=400, easing=KEasing.OUT_CUBIC,
            parent=self,
        )

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