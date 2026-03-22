"""
KDialog — custom modal dialog with animated appearance.

During animation the real box widget is hidden and a grabbed pixmap
is painted with scale + opacity transforms.  Once the open animation
completes the real widget is shown so buttons become interactive.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import (
    Qt, QRectF, QPropertyAnimation, QEasingCurve,
    pyqtProperty, pyqtSignal,
)
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath

from core.theme import ThemeManager
from widgets.klabel import KLabel
from widgets.kbutton import KButton


class KDialog(QWidget):
    """
    Animated modal dialog.

    Usage::

        dialog = KDialog(parent, "Title", "Message text")
        dialog.add_button("Cancel", dialog.reject)
        dialog.add_button("OK", dialog.accept)
        dialog.show_dialog()
    """

    accepted = pyqtSignal()
    rejected = pyqtSignal()

    BOX_W = 400
    BOX_H = 220
    ANIM_OPEN_MS = 250
    ANIM_CLOSE_MS = 200

    def __init__(self, parent: QWidget, title: str, text: str = ""):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._tm = ThemeManager.instance()
        self._tm.changed.connect(self._on_theme_changed)

        self._anim_val = 0.0
        self._is_closing = False
        self._box_pixmap = None  # cached snapshot used during animation

        self._build_ui(title, text)

        self.setGeometry(0, 0, parent.width(), parent.height())
        self.hide()

    # ── build ───────────────────────────────────────

    def _build_ui(self, title: str, text: str):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._box = QWidget()
        self._box.setFixedSize(self.BOX_W, self.BOX_H)
        main_layout.addWidget(self._box, 0, Qt.AlignmentFlag.AlignCenter)

        box_layout = QVBoxLayout(self._box)
        box_layout.setContentsMargins(32, 28, 32, 24)
        box_layout.setSpacing(12)

        self._title_lbl = KLabel(title, style="heading", font_size=22,
                                 align=Qt.AlignmentFlag.AlignCenter)
        box_layout.addWidget(self._title_lbl)

        if text:
            self._text_lbl = KLabel(text, style="body",
                                    align=Qt.AlignmentFlag.AlignCenter)
            box_layout.addWidget(self._text_lbl)

        box_layout.addStretch()

        self._btn_layout = QHBoxLayout()
        self._btn_layout.setSpacing(12)
        box_layout.addLayout(self._btn_layout)

        self._apply_box_style()

    def _apply_box_style(self):
        t = self._tm
        self._box.setObjectName("_KDialogBox")
        self._box.setStyleSheet(
            f"QWidget#_KDialogBox {{"
            f"    background: {t.bg};"
            f"    border: 1.5px solid {t.border};"
            f"    border-radius: 12px;"
            f"}}"
        )

    def _on_theme_changed(self):
        self._apply_box_style()
        self.update()

    # ── public API ──────────────────────────────────

    def add_button(self, text: str, callback=None):
        btn = KButton(text, on_click=lambda: self._on_btn_click(callback))
        self._btn_layout.addWidget(btn)
        return btn

    def _on_btn_click(self, callback):
        if self._is_closing:
            return
        if callback:
            callback()
        else:
            self.close_dialog()

    def accept(self):
        if self._is_closing:
            return
        self.accepted.emit()
        self.close_dialog()

    def reject(self):
        if self._is_closing:
            return
        self.rejected.emit()
        self.close_dialog()

    # ── animation property ──────────────────────────

    def _get_anim(self) -> float:
        return self._anim_val

    def _set_anim(self, v: float):
        self._anim_val = v
        if self.parent():
            pw, ph = self.parent().width(), self.parent().height()
            if self.width() != pw or self.height() != ph:
                self.setGeometry(0, 0, pw, ph)
        self.update()

    animVal = pyqtProperty(float, _get_anim, _set_anim)

    # ── show / close ────────────────────────────────

    def show_dialog(self):
        self._apply_box_style()
        self.raise_()
        self.show()
        self.setFocus()

        # Grab a snapshot of the fully-rendered box
        self._box.show()
        self._box.repaint()
        self._box_pixmap = self._box.grab()
        self._box.hide()  # hide real box during animation

        self._anim = QPropertyAnimation(self, b"animVal")
        self._anim.setDuration(self.ANIM_OPEN_MS)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.finished.connect(self._on_open_done)
        self._anim.start()

    def _on_open_done(self):
        self._box_pixmap = None
        self._box.show()  # real box is now interactive

    def close_dialog(self):
        if self._is_closing:
            return
        self._is_closing = True

        # Grab snapshot and hide real box
        self._box_pixmap = self._box.grab()
        self._box.hide()

        self._anim = QPropertyAnimation(self, b"animVal")
        self._anim.setDuration(self.ANIM_CLOSE_MS)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._anim.finished.connect(self.close)
        self._anim.start()

    # ── paint ───────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        t = self._tm
        w = self.width()
        h = self.height()
        v = self._anim_val

        # 1. Dimmed overlay
        overlay_alpha = int(v * 120)
        if t.is_dark:
            overlay = QColor(0, 0, 0, overlay_alpha)
        else:
            overlay = QColor(0, 0, 0, overlay_alpha)
        p.fillRect(0, 0, w, h, overlay)

        # 2. Animated box pixmap (during open/close animation)
        if self._box_pixmap is not None:
            bw = self._box.width()
            bh = self._box.height()

            scale = 0.85 + 0.15 * v

            p.setOpacity(v)
            p.translate(w / 2, h / 2)
            p.scale(scale, scale)
            p.translate(-bw / 2, -bh / 2)

            # Create a rounded path to clip the pixmap
            path = QPainterPath()
            path.addRoundedRect(QRectF(0, 0, bw, bh), 12, 12)
            p.setClipPath(path)

            p.drawPixmap(0, 0, self._box_pixmap)

        p.end()

    # ── input blocking ──────────────────────────────

    def mousePressEvent(self, event):
        event.accept()
        
    def mouseReleaseEvent(self, event):
        event.accept()

    def wheelEvent(self, event):
        event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        else:
            event.accept()
