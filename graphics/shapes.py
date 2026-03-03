"""
Shape primitives and color utilities.

Usage:
    from graphics.shapes import Shapes, Color

    # in KCanvas.on_draw(painter):
    Shapes.rect(painter, 10, 10, 100, 50, color="#FF0000", radius=8)
    Shapes.circle(painter, 200, 100, 40, color=Color.WHITE)
    Shapes.line(painter, 0, 0, 100, 100, color="#00FF00", width=2)
    Shapes.text(painter, "Hello", 50, 50, color="#FFFFFF", size=24)
"""

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPolygonF


class Color:
    """Common color constants."""
    BLACK = "#000000"
    WHITE = "#FFFFFF"
    RED = "#FF0000"
    GREEN = "#00FF00"
    BLUE = "#0000FF"
    YELLOW = "#FFFF00"
    CYAN = "#00FFFF"
    MAGENTA = "#FF00FF"
    GRAY = "#808080"
    DARK_GRAY = "#404040"
    LIGHT_GRAY = "#C0C0C0"
    TRANSPARENT = "transparent"

    @staticmethod
    def from_rgb(r: int, g: int, b: int, a: int = 255) -> QColor:
        return QColor(r, g, b, a)

    @staticmethod
    def from_hex(hex_str: str) -> QColor:
        return QColor(hex_str)

    @staticmethod
    def with_alpha(color: str, alpha: int) -> QColor:
        """Create color with alpha (0-255)."""
        c = QColor(color)
        c.setAlpha(alpha)
        return c


class Shapes:
    """Static methods to draw shapes on QPainter."""

    @staticmethod
    def rect(
        painter: QPainter,
        x: float, y: float,
        width: float, height: float,
        *,
        color: str | QColor = Color.WHITE,
        border: str | QColor | None = None,
        border_width: float = 1.0,
        radius: float = 0,
        fill: bool = True,
    ):
        """
        Draw a rectangle.

        radius: corner radius (0 = sharp corners)
        border: outline color (None = no outline)
        fill: False = only outline
        """
        rect = QRectF(x, y, width, height)

        # fill
        if fill:
            brush_color = QColor(color) if isinstance(color, str) else color
            painter.setBrush(QBrush(brush_color))
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)

        # border
        if border:
            pen_color = QColor(border) if isinstance(border, str) else border
            pen = QPen(pen_color, border_width)
            painter.setPen(pen)
        else:
            painter.setPen(Qt.PenStyle.NoPen)

        if radius > 0:
            painter.drawRoundedRect(rect, radius, radius)
        else:
            painter.drawRect(rect)

    @staticmethod
    def circle(
        painter: QPainter,
        cx: float, cy: float,
        radius: float,
        *,
        color: str | QColor = Color.WHITE,
        border: str | QColor | None = None,
        border_width: float = 1.0,
        fill: bool = True,
    ):
        """Draw a circle centered at (cx, cy)."""
        rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)

        if fill:
            brush_color = QColor(color) if isinstance(color, str) else color
            painter.setBrush(QBrush(brush_color))
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)

        if border:
            pen_color = QColor(border) if isinstance(border, str) else border
            painter.setPen(QPen(pen_color, border_width))
        else:
            painter.setPen(Qt.PenStyle.NoPen)

        painter.drawEllipse(rect)

    @staticmethod
    def ellipse(
        painter: QPainter,
        x: float, y: float,
        width: float, height: float,
        *,
        color: str | QColor = Color.WHITE,
        border: str | QColor | None = None,
        border_width: float = 1.0,
        fill: bool = True,
    ):
        """Draw an ellipse."""
        rect = QRectF(x, y, width, height)

        if fill:
            brush_color = QColor(color) if isinstance(color, str) else color
            painter.setBrush(QBrush(brush_color))
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)

        if border:
            pen_color = QColor(border) if isinstance(border, str) else border
            painter.setPen(QPen(pen_color, border_width))
        else:
            painter.setPen(Qt.PenStyle.NoPen)

        painter.drawEllipse(rect)

    @staticmethod
    def line(
        painter: QPainter,
        x1: float, y1: float,
        x2: float, y2: float,
        *,
        color: str | QColor = Color.WHITE,
        width: float = 1.0,
        cap: Qt.PenCapStyle = Qt.PenCapStyle.RoundCap,
    ):
        """Draw a line."""
        pen_color = QColor(color) if isinstance(color, str) else color
        pen = QPen(pen_color, width)
        pen.setCapStyle(cap)
        painter.setPen(pen)
        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

    @staticmethod
    def polygon(
        painter: QPainter,
        points: list[tuple[float, float]],
        *,
        color: str | QColor = Color.WHITE,
        border: str | QColor | None = None,
        border_width: float = 1.0,
        fill: bool = True,
    ):
        """Draw a polygon from list of (x, y) points."""
        if len(points) < 3:
            return

        poly = QPolygonF([QPointF(p[0], p[1]) for p in points])

        if fill:
            brush_color = QColor(color) if isinstance(color, str) else color
            painter.setBrush(QBrush(brush_color))
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)

        if border:
            pen_color = QColor(border) if isinstance(border, str) else border
            painter.setPen(QPen(pen_color, border_width))
        else:
            painter.setPen(Qt.PenStyle.NoPen)

        painter.drawPolygon(poly)

    @staticmethod
    def triangle(
        painter: QPainter,
        x1: float, y1: float,
        x2: float, y2: float,
        x3: float, y3: float,
        *,
        color: str | QColor = Color.WHITE,
        border: str | QColor | None = None,
        border_width: float = 1.0,
        fill: bool = True,
    ):
        """Draw a triangle."""
        Shapes.polygon(
            painter,
            [(x1, y1), (x2, y2), (x3, y3)],
            color=color,
            border=border,
            border_width=border_width,
            fill=fill,
        )

    @staticmethod
    def arc(
        painter: QPainter,
        x: float, y: float,
        width: float, height: float,
        start_angle: float,
        span_angle: float,
        *,
        color: str | QColor = Color.WHITE,
        line_width: float = 2.0,
    ):
        """
        Draw an arc.

        Angles in degrees (Qt uses 1/16th degrees internally).
        start_angle: starting angle (0 = 3 o'clock)
        span_angle: sweep angle (positive = counter-clockwise)
        """
        rect = QRectF(x, y, width, height)
        pen_color = QColor(color) if isinstance(color, str) else color
        painter.setPen(QPen(pen_color, line_width))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(rect, int(start_angle * 16), int(span_angle * 16))

    @staticmethod
    def text(
        painter: QPainter,
        text: str,
        x: float, y: float,
        *,
        color: str | QColor = Color.WHITE,
        size: int = 14,
        font_family: str = "Roboto",
        bold: bool = True,
        align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
        max_width: float = 0,
    ):
        """
        Draw text.

        If max_width > 0, text is wrapped/clipped to that width.
        """
        pen_color = QColor(color) if isinstance(color, str) else color
        painter.setPen(pen_color)

        weight = QFont.Weight.Bold if bold else QFont.Weight.Normal
        font = QFont(font_family, size, weight)
        painter.setFont(font)

        if max_width > 0:
            rect = QRectF(x, y, max_width, 10000)
            painter.drawText(rect, int(align), text)
        else:
            painter.drawText(QPointF(x, y + size), text)

    @staticmethod
    def point(
        painter: QPainter,
        x: float, y: float,
        *,
        color: str | QColor = Color.WHITE,
        size: float = 4.0,
    ):
        """Draw a point (small filled circle)."""
        Shapes.circle(painter, x, y, size / 2, color=color)