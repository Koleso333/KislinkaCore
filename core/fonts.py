"""
Font manager.

Ensures fonts are applied correctly regardless of QSS.
All widgets should use Fonts.heading() / Fonts.body() instead of raw QFont().

    from core.fonts import Fonts

    label.setFont(Fonts.heading(28))
    button.setFont(Fonts.body(14))
"""

from pathlib import Path
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication


FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

# actual registered family names (filled on load)
_heading_family: str = "Mitr"
_body_family: str = "Roboto"
_loaded: bool = False


def _log(msg: str):
    print(f"[Fonts] {msg}")


def load_fonts():
    """Load all fonts from assets/fonts/ and register them."""
    global _heading_family, _body_family, _loaded

    if _loaded:
        return

    if not FONTS_DIR.exists():
        _log(f"⚠ Fonts dir missing: {FONTS_DIR}")
        _loaded = True
        return

    for fp in sorted(FONTS_DIR.iterdir()):
        if fp.suffix.lower() not in (".ttf", ".otf"):
            continue

        fid = QFontDatabase.addApplicationFont(str(fp))
        if fid < 0:
            _log(f"⚠ Failed: {fp.name}")
            continue

        families = QFontDatabase.applicationFontFamilies(fid)
        _log(f"Loaded: {fp.name} → {families}")

        # detect heading / body font by filename
        name_lower = fp.stem.lower()
        if families:
            if "mitr" in name_lower:
                _heading_family = families[0]
            elif "roboto" in name_lower:
                _body_family = families[0]

    _loaded = True
    _log(f"Heading font: '{_heading_family}'")
    _log(f"Body font: '{_body_family}'")

    # set application default font
    app = QApplication.instance()
    if app:
        default = QFont(_body_family, 14)
        default.setWeight(QFont.Weight.Bold)
        app.setFont(default)
        _log("Default app font set ✓")


class Fonts:
    """Font factory. Use these instead of QFont() directly."""

    @staticmethod
    def heading_family() -> str:
        return _heading_family

    @staticmethod
    def body_family() -> str:
        return _body_family

    @staticmethod
    def heading(size: int = 28) -> QFont:
        """Mitr — for titles and headings."""
        f = QFont(_heading_family, size)
        return f

    @staticmethod
    def body(size: int = 14) -> QFont:
        """Roboto Bold — for everything else."""
        f = QFont(_body_family, size)
        f.setWeight(QFont.Weight.Bold)
        return f

    @staticmethod
    def custom(family: str, size: int = 14, bold: bool = False) -> QFont:
        """Any font."""
        f = QFont(family, size)
        if bold:
            f.setWeight(QFont.Weight.Bold)
        return f