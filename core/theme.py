"""
Theme system. Two built-in themes: pure B&W dark and light.
Font declarations REMOVED from QSS — handled by Fonts module.
"""

from PyQt6.QtCore import QObject, pyqtSignal
from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    name: str
    bg: str
    fg: str
    bg_alt: str
    fg_dim: str
    border: str
    disabled: str
    hover: str
    scrollbar: str


DARK = Theme(
    name="dark",
    bg="#000000", fg="#FFFFFF", bg_alt="#0D0D0D",
    fg_dim="#666666", border="#FFFFFF", disabled="#3A3A3A",
    hover="#1A1A1A", scrollbar="#2A2A2A",
)

LIGHT = Theme(
    name="light",
    bg="#FFFFFF", fg="#000000", bg_alt="#F2F2F2",
    fg_dim="#999999", border="#000000", disabled="#C5C5C5",
    hover="#E5E5E5", scrollbar="#D5D5D5",
)

_THEMES: dict[str, Theme] = {"dark": DARK, "light": LIGHT}


class ThemeManager(QObject):

    changed = pyqtSignal()
    _instance: "ThemeManager | None" = None

    def __init__(self):
        if ThemeManager._instance is not None:
            raise RuntimeError("Use ThemeManager.instance()")
        super().__init__()
        self._theme: Theme = DARK
        ThemeManager._instance = self

    @classmethod
    def instance(cls) -> "ThemeManager":
        if cls._instance is None:
            cls()
        return cls._instance

    @property
    def theme(self) -> Theme:
        return self._theme

    @property
    def is_dark(self) -> bool:
        return self._theme.name == "dark"

    @property
    def bg(self)        -> str: return self._theme.bg
    @property
    def fg(self)        -> str: return self._theme.fg
    @property
    def bg_alt(self)    -> str: return self._theme.bg_alt
    @property
    def fg_dim(self)    -> str: return self._theme.fg_dim
    @property
    def border(self)    -> str: return self._theme.border
    @property
    def disabled(self)  -> str: return self._theme.disabled
    @property
    def hover(self)     -> str: return self._theme.hover
    @property
    def scrollbar(self) -> str: return self._theme.scrollbar

    def set_theme(self, name: str) -> None:
        if name in _THEMES and name != self._theme.name:
            self._theme = _THEMES[name]
            self.changed.emit()

    def toggle(self) -> None:
        self.set_theme("light" if self.is_dark else "dark")

    def base_qss(self) -> str:
        """
        Minimal global stylesheet.
        NO font declarations — Fonts module handles that.
        """
        t = self._theme
        return f"""
            * {{ margin: 0; padding: 0; }}

            QWidget {{
                background: {t.bg};
                color: {t.fg};
                border: none;
            }}

            QScrollBar:vertical {{
                background: transparent; width: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {t.scrollbar}; border-radius: 3px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: none; height: 0;
            }}
            QScrollBar:horizontal {{
                background: transparent; height: 6px;
            }}
            QScrollBar::handle:horizontal {{
                background: {t.scrollbar}; border-radius: 3px;
                min-width: 30px;
            }}
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal,
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {{
                background: none; width: 0;
            }}
        """