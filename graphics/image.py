"""
Image loading, drawing, and manipulation.

Usage:
    from graphics.image import KImage

    img = KImage("path/to/image.png")
    img.draw(painter, 10, 10)
    img.draw(painter, 10, 10, width=100, height=100)  # scaled
    img.draw(painter, 10, 10, opacity=0.5)

    # manipulations (return new KImage)
    scaled = img.scaled(200, 200)
    rotated = img.rotated(45)
    flipped = img.flipped(horizontal=True)
"""

from pathlib import Path

from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import (
    QPixmap, QPainter, QImage, QTransform, QColor,
)


def _log(msg: str):
    print(f"[KImage] {msg}")


class KImage:
    """
    Wrapper around QPixmap with convenient methods.
    """

    def __init__(self, source: str | Path | QPixmap | QImage | None = None):
        """
        Create from:
          - file path (str / Path)
          - QPixmap
          - QImage
          - None (empty image)
        """
        self._pixmap: QPixmap = QPixmap()

        if source is None:
            pass
        elif isinstance(source, QPixmap):
            self._pixmap = source
        elif isinstance(source, QImage):
            self._pixmap = QPixmap.fromImage(source)
        elif isinstance(source, (str, Path)):
            path = Path(source)
            if path.exists():
                self._pixmap = QPixmap(str(path))
                if self._pixmap.isNull():
                    _log(f"⚠ Failed to load: {path}")
            else:
                _log(f"⚠ File not found: {path}")

    @classmethod
    def from_bytes(cls, data: bytes) -> "KImage":
        """Create from raw image bytes (PNG, JPG, etc.)."""
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        return cls(pixmap)

    @classmethod
    def create(cls, width: int, height: int, fill: str | QColor = "#00000000") -> "KImage":
        """Create a blank image of given size."""
        pixmap = QPixmap(width, height)
        color = QColor(fill) if isinstance(fill, str) else fill
        pixmap.fill(color)
        return cls(pixmap)

    # ── properties ──────────────────────────────────

    @property
    def pixmap(self) -> QPixmap:
        return self._pixmap

    @property
    def width(self) -> int:
        return self._pixmap.width()

    @property
    def height(self) -> int:
        return self._pixmap.height()

    @property
    def size(self) -> tuple[int, int]:
        return (self.width, self.height)

    @property
    def is_valid(self) -> bool:
        return not self._pixmap.isNull()

    # ── drawing ─────────────────────────────────────

    def draw(
        self,
        painter: QPainter,
        x: float, y: float,
        width: float = 0,
        height: float = 0,
        *,
        opacity: float = 1.0,
        smooth: bool = True,
    ):
        """
        Draw image at (x, y).

        width/height: if > 0, scale to fit
        opacity: 0.0–1.0
        smooth: use smooth scaling transformation
        """
        if not self.is_valid:
            return

        old_opacity = painter.opacity()
        painter.setOpacity(old_opacity * opacity)

        if smooth:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        if width > 0 and height > 0:
            target = QRectF(x, y, width, height)
            source = QRectF(0, 0, self.width, self.height)
            painter.drawPixmap(target, self._pixmap, source)
        else:
            painter.drawPixmap(QPointF(x, y), self._pixmap)

        painter.setOpacity(old_opacity)

    def draw_centered(
        self,
        painter: QPainter,
        cx: float, cy: float,
        width: float = 0,
        height: float = 0,
        *,
        opacity: float = 1.0,
    ):
        """Draw image centered at (cx, cy)."""
        w = width if width > 0 else self.width
        h = height if height > 0 else self.height
        self.draw(painter, cx - w / 2, cy - h / 2, width, height, opacity=opacity)

    def draw_tiled(
        self,
        painter: QPainter,
        x: float, y: float,
        width: float,
        height: float,
    ):
        """Tile image to fill area."""
        if not self.is_valid or self.width == 0 or self.height == 0:
            return

        for ty in range(int(y), int(y + height), self.height):
            for tx in range(int(x), int(x + width), self.width):
                painter.drawPixmap(QPointF(tx, ty), self._pixmap)

    # ── transformations (return new KImage) ─────────

    def scaled(
        self,
        width: int,
        height: int,
        keep_aspect: bool = True,
        smooth: bool = True,
    ) -> "KImage":
        """Return scaled copy."""
        if not self.is_valid:
            return KImage()

        mode = (Qt.AspectRatioMode.KeepAspectRatio
                if keep_aspect else Qt.AspectRatioMode.IgnoreAspectRatio)
        transform = (Qt.TransformationMode.SmoothTransformation
                     if smooth else Qt.TransformationMode.FastTransformation)

        new_pixmap = self._pixmap.scaled(width, height, mode, transform)
        return KImage(new_pixmap)

    def scaled_to_width(self, width: int, smooth: bool = True) -> "KImage":
        """Scale to width, keep aspect ratio."""
        if not self.is_valid or self.width == 0:
            return KImage()
        ratio = width / self.width
        new_height = int(self.height * ratio)
        return self.scaled(width, new_height, keep_aspect=False, smooth=smooth)

    def scaled_to_height(self, height: int, smooth: bool = True) -> "KImage":
        """Scale to height, keep aspect ratio."""
        if not self.is_valid or self.height == 0:
            return KImage()
        ratio = height / self.height
        new_width = int(self.width * ratio)
        return self.scaled(new_width, height, keep_aspect=False, smooth=smooth)

    def rotated(self, angle: float, smooth: bool = True) -> "KImage":
        """Return rotated copy (angle in degrees)."""
        if not self.is_valid:
            return KImage()

        transform = QTransform().rotate(angle)
        mode = (Qt.TransformationMode.SmoothTransformation
                if smooth else Qt.TransformationMode.FastTransformation)
        new_pixmap = self._pixmap.transformed(transform, mode)
        return KImage(new_pixmap)

    def flipped(self, horizontal: bool = False, vertical: bool = False) -> "KImage":
        """Return flipped copy."""
        if not self.is_valid:
            return KImage()

        transform = QTransform()
        if horizontal:
            transform.scale(-1, 1)
        if vertical:
            transform.scale(1, -1)

        new_pixmap = self._pixmap.transformed(transform)
        return KImage(new_pixmap)

    def cropped(self, x: int, y: int, width: int, height: int) -> "KImage":
        """Return cropped copy."""
        if not self.is_valid:
            return KImage()
        new_pixmap = self._pixmap.copy(x, y, width, height)
        return KImage(new_pixmap)

    def to_grayscale(self) -> "KImage":
        """Return grayscale copy."""
        if not self.is_valid:
            return KImage()
        image = self._pixmap.toImage()
        gray = image.convertToFormat(QImage.Format.Format_Grayscale8)
        return KImage(QPixmap.fromImage(gray))

    # ── save ────────────────────────────────────────

    def save(self, path: str | Path, quality: int = 90) -> bool:
        """Save to file (format detected from extension)."""
        if not self.is_valid:
            return False
        return self._pixmap.save(str(path), quality=quality)