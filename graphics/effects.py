"""
Image effects: tint, opacity, invert, round corners, shadow.

Usage:
    from graphics.effects import Effects

    tinted = Effects.tint(image, "#FF0000", strength=0.5)
    faded = Effects.opacity(image, 0.5)
    inverted = Effects.invert(image)
    rounded = Effects.round_corners(image, radius=20)
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import (
    QPixmap, QImage, QPainter, QColor, QPainterPath,
)

from graphics.image import KImage


class Effects:
    """Static methods for image effects."""

    @staticmethod
    def tint(image: KImage, color: str | QColor, strength: float = 0.5) -> KImage:
        """
        Apply color tint.

        strength: 0.0 = no tint, 1.0 = full color overlay
        """
        if not image.is_valid:
            return KImage()

        strength = max(0.0, min(1.0, strength))
        tint_color = QColor(color) if isinstance(color, str) else color
        tint_color.setAlpha(int(255 * strength))

        result = QImage(image.width, image.height, QImage.Format.Format_ARGB32_Premultiplied)
        result.fill(Qt.GlobalColor.transparent)

        p = QPainter(result)
        p.drawPixmap(0, 0, image.pixmap)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
        p.fillRect(result.rect(), tint_color)
        p.end()

        return KImage(QPixmap.fromImage(result))

    @staticmethod
    def opacity(image: KImage, alpha: float) -> KImage:
        """
        Adjust opacity.

        alpha: 0.0 = fully transparent, 1.0 = original
        """
        if not image.is_valid:
            return KImage()

        alpha = max(0.0, min(1.0, alpha))

        result = QImage(image.width, image.height, QImage.Format.Format_ARGB32_Premultiplied)
        result.fill(Qt.GlobalColor.transparent)

        p = QPainter(result)
        p.setOpacity(alpha)
        p.drawPixmap(0, 0, image.pixmap)
        p.end()

        return KImage(QPixmap.fromImage(result))

    @staticmethod
    def invert(image: KImage) -> KImage:
        """Invert colors."""
        if not image.is_valid:
            return KImage()

        img = image.pixmap.toImage()
        img.invertPixels()
        return KImage(QPixmap.fromImage(img))

    @staticmethod
    def round_corners(image: KImage, radius: float) -> KImage:
        """Apply rounded corners mask."""
        if not image.is_valid:
            return KImage()

        result = QImage(image.width, image.height, QImage.Format.Format_ARGB32_Premultiplied)
        result.fill(Qt.GlobalColor.transparent)

        p = QPainter(result)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(0, 0, image.width, image.height, radius, radius)
        p.setClipPath(path)

        p.drawPixmap(0, 0, image.pixmap)
        p.end()

        return KImage(QPixmap.fromImage(result))