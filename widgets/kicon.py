"""
SVG icon loader with theme-aware recoloring.
Core icons are embedded — no external files needed.
"""

from pathlib import Path

from PyQt6.QtCore import QByteArray, Qt, QRectF
from PyQt6.QtGui import QPixmap, QPainter, QIcon, QPen, QColor

# ── try SVG renderer ────────────────────────────────────────
try:
    from PyQt6.QtSvg import QSvgRenderer
    _HAS_SVG = True
except ImportError:
    _HAS_SVG = False


# ── embedded SVGs (stroke = #FFFFFF as template) ────────────

_EMBEDDED: dict[str, str] = {

    "close": (
        '<svg width="16" height="16" viewBox="0 0 16 16"'
        ' xmlns="http://www.w3.org/2000/svg">'
        '<line x1="4" y1="4" x2="12" y2="12"'
        ' stroke="#FFFFFF" stroke-width="1.5" stroke-linecap="round"/>'
        '<line x1="12" y1="4" x2="4" y2="12"'
        ' stroke="#FFFFFF" stroke-width="1.5" stroke-linecap="round"/>'
        '</svg>'
    ),

    "minimize": (
        '<svg width="16" height="16" viewBox="0 0 16 16"'
        ' xmlns="http://www.w3.org/2000/svg">'
        '<line x1="4" y1="8" x2="12" y2="8"'
        ' stroke="#FFFFFF" stroke-width="1.5" stroke-linecap="round"/>'
        '</svg>'
    ),

    "settings": (
        '<svg width="24" height="24" viewBox="0 0 24 24"'
        ' xmlns="http://www.w3.org/2000/svg" fill="none">'
        '<circle cx="12" cy="12" r="3" stroke="#FFFFFF" stroke-width="2"/>'
        '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25'
        'a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 '
        '.73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09'
        'a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 '
        '1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 '
        '2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 '
        '0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-'
        '1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38'
        'a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-'
        '1-1.73V4a2 2 0 0 0-2-2z" stroke="#FFFFFF" stroke-width="2"/>'
        '</svg>'
    ),

    "back": (
        '<svg width="16" height="16" viewBox="0 0 16 16"'
        ' xmlns="http://www.w3.org/2000/svg">'
        '<polyline points="10,3 5,8 10,13"'
        ' stroke="#FFFFFF" stroke-width="1.5" stroke-linecap="round"'
        ' stroke-linejoin="round" fill="none"/>'
        '</svg>'
    ),
}


# ── QPainter fallback shapes (if QtSvg missing) ────────────

def _fallback_pixmap(name: str, color: str, size: int) -> QPixmap:
    """Draw minimal icon shapes when QSvgRenderer unavailable."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), 1.5)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)

    m = size * 0.25  # margin
    s = size - m      # end

    if name == "close":
        p.drawLine(int(m), int(m), int(s), int(s))
        p.drawLine(int(s), int(m), int(m), int(s))
    elif name == "minimize":
        mid = size // 2
        p.drawLine(int(m), mid, int(s), mid)
    elif name == "settings":
        r = size * 0.2
        p.drawEllipse(int(size / 2 - r), int(size / 2 - r), int(r * 2), int(r * 2))
    elif name == "back":
        mid = size // 2
        p.drawLine(int(s * 0.6), int(m), int(m), mid)
        p.drawLine(int(m), mid, int(s * 0.6), int(s))
    p.end()
    return pix


# ── public API ──────────────────────────────────────────────

def load_svg_icon(
    name_or_path: str,
    color: str = "#FFFFFF",
    size: int = 16,
) -> QIcon:
    """
    Load an SVG icon with colour replacement.

    name_or_path:
        Embedded name  ("close", "minimize", "settings", "back")
        OR  path to an SVG file on disk.
    color:
        Hex colour string.  Replaces the template #FFFFFF.
    size:
        Pixel size of the resulting square icon.
    """
    # ── resolve SVG source ──────────────────────────
    svg_text: str | None = None

    if name_or_path in _EMBEDDED:
        svg_text = _EMBEDDED[name_or_path]
    else:
        path = Path(name_or_path)
        if path.is_file():
            svg_text = path.read_text(encoding="utf-8")

    # ── recolour ────────────────────────────────────
    if svg_text is not None:
        svg_text = svg_text.replace("#FFFFFF", color).replace("#ffffff", color)

    # ── render with QSvgRenderer ────────────────────
    if svg_text and _HAS_SVG:
        renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))
        if renderer.isValid():
            pix = QPixmap(size, size)
            pix.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pix)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            renderer.render(painter, QRectF(0, 0, size, size))
            painter.end()
            return QIcon(pix)

    # ── fallback ────────────────────────────────────
    if name_or_path in _EMBEDDED:
        return QIcon(_fallback_pixmap(name_or_path, color, size))

    return QIcon()