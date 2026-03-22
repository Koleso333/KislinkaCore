from __future__ import annotations

from PyQt6.QtWidgets import QComboBox, QStyleOptionComboBox, QStyle
from PyQt6.QtCore import QRectF, Qt, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QPainter

from core.theme import ThemeManager
from core.fonts import Fonts
from widgets.kicon import load_svg_icon


class KDropdown(QComboBox):
    def __init__(
        self,
        items: list[str] | None = None,
        *,
        placeholder: str = "",
        font_size: int = 14,
        editable: bool = False,
        parent=None,
    ):
        super().__init__(parent)

        self.setFont(Fonts.body(font_size))
        self.setEditable(editable)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        if placeholder:
            self.setPlaceholderText(placeholder)

        if items:
            self.addItems([str(x) for x in items])

        self._tm = ThemeManager.instance()

        self._arrow_angle = 0.0
        self._arrow_anim = QPropertyAnimation(self, b"arrowAngle")
        self._arrow_anim.setDuration(140)
        self._arrow_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._apply_theme()
        self._tm.changed.connect(self._apply_theme)

    def set_items(self, items: list[str]) -> None:
        self.clear()
        self.addItems([str(x) for x in items])

    def _apply_theme(self) -> None:
        t = self._tm
        self.setStyleSheet(
            f"""
            QComboBox {{
                background: {t.bg_alt};
                color: {t.fg};
                border: 1.5px solid {t.border};
                border-radius: 6px;
                padding: 6px 10px;
                padding-right: 26px;
                min-height: 28px;
            }}
            QComboBox:disabled {{
                background: {t.bg_alt};
                color: {t.fg_dim};
                border: 1.5px solid {t.disabled};
            }}
            QComboBox:hover:enabled {{
                background: {t.hover};
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 22px;
                border-left: 1px solid {t.border};
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
                background: transparent;
            }}
            QComboBox::down-arrow {{
                image: none;
                width: 0;
                height: 0;
            }}
            QComboBox QAbstractItemView {{
                background: {t.bg_alt};
                color: {t.fg};
                border: 1px solid {t.border};
                selection-background-color: {t.fg};
                selection-color: {t.bg};
                outline: 0;
            }}
            """
        )

    # ── animated arrow ─────────────────────────────

    def _get_arrow_angle(self) -> float:
        return self._arrow_angle

    def _set_arrow_angle(self, v: float) -> None:
        self._arrow_angle = v
        self.update()

    arrowAngle = pyqtProperty(float, _get_arrow_angle, _set_arrow_angle)

    def _animate_arrow(self, target: float) -> None:
        self._arrow_anim.stop()
        self._arrow_anim.setStartValue(self._arrow_angle)
        self._arrow_anim.setEndValue(target)
        self._arrow_anim.start()

    def showPopup(self) -> None:
        self._animate_arrow(180.0)
        super().showPopup()

    def hidePopup(self) -> None:
        self._animate_arrow(0.0)
        super().hidePopup()

    def wheelEvent(self, event) -> None:
        # Ignore wheel events to prevent accidental scroll changes
        event.ignore()

    def paintEvent(self, event) -> None:
        # Let Qt draw the control itself
        super().paintEvent(event)

        # Draw our arrow icon on top with rotation.
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        t = self._tm
        color = t.fg if self.isEnabled() else t.fg_dim
        ico = load_svg_icon("down", color=color, size=14)
        pm = ico.pixmap(14, 14)

        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        r = self.style().subControlRect(
            QStyle.ComplexControl.CC_ComboBox,
            opt,
            QStyle.SubControl.SC_ComboBoxArrow,
            self,
        )

        cx = r.center().x()
        cy = r.center().y()
        target = QRectF(cx - 7, cy - 7, 14, 14)

        p.translate(cx, cy)
        p.rotate(self._arrow_angle)
        p.translate(-cx, -cy)
        p.drawPixmap(target.toRect(), pm)
        p.end()
