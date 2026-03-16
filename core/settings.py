"""
Built-in Settings panel with localization and persistent theme/language.
"""

import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
)
from PyQt6.QtCore import Qt, QSize, QTimer

from core.theme import ThemeManager
from core.scene import Scene, SceneManager, AnimationType
from core.permissions import PermissionManager, Permission
from core.fonts import Fonts
from core.storage import StorageManager
from core.locale import LocaleManager
from core.hooks import HookManager
from widgets.klabel import KLabel
from widgets.kbutton import KButton
from widgets.ktoggle import KToggle
from widgets.kicon import load_svg_icon
from widgets.kscrollarea import KScrollArea


CORE_INFO_PATH = Path(__file__).resolve().parent / "core_info.json"

def sip_deleted(obj) -> bool:
    """Check if a Qt object has been deleted."""
    try:
        # accessing any property will raise if deleted
        obj.objectName()
        return False
    except RuntimeError:
        return True


def _load_core_info() -> dict:
    try:
        return json.loads(CORE_INFO_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"name": "KislinkaCore", "version": "?", "author": "?"}


class SettingsPanel:

    def __init__(self, scene_manager: SceneManager, titlebar=None):
        self._sm = scene_manager
        self._pm = PermissionManager.instance()
        self._tm = ThemeManager.instance()
        self._storage = StorageManager.instance()
        self._loc = LocaleManager.instance()
        self._titlebar = titlebar
        self._is_open = False
        self._entry_depth = 0
        self._app_manifest = None
        self._core_info = _load_core_info()

        self._register_core_tabs()

    def set_titlebar(self, titlebar):
        self._titlebar = titlebar

    @property
    def is_open(self) -> bool:
        return self._is_open

    def snapshot(self) -> dict:
        """Capture current settings navigation state to restore after visual reload."""
        if not self._is_open:
            return {"is_open": False}

        current_name = "settings_menu"
        try:
            cur = getattr(self._sm, "current", None)
            if cur is not None:
                current_name = getattr(cur, "name", "settings_menu") or "settings_menu"
        except Exception:
            pass

        return {
            "is_open": True,
            "current": current_name,
        }

    def restore(self, snap: dict | None):
        """Restore settings navigation state captured by snapshot()."""
        if not snap or not isinstance(snap, dict):
            return
        if not snap.get("is_open"):
            return

        if not self._is_open:
            self.open()

        target = snap.get("current", "settings_menu")
        try:
            if getattr(self._sm, "current", None) is not None and self._sm.current.name == target:
                return
        except Exception:
            pass
        builder = self._builder_for_scene(target)
        if builder and not self._sm.is_animating:
            # menu is already on stack after open(); push target page if needed
            if target != "settings_menu":
                self._sm.push(builder(), AnimationType.NONE)

    def _builder_for_scene(self, scene_name: str):
        if scene_name == "settings_menu":
            return self._build_menu
        if scene_name == "settings_themes":
            return self._build_themes_page
        if scene_name == "settings_language":
            return self._build_language_page
        if scene_name == "settings_about":
            return self._build_about_page
        if scene_name == "settings_core_about":
            return self._build_core_about_page
        return None

    def set_app_manifest(self, manifest):
        self._app_manifest = manifest

    def open(self):
        if self._is_open or self._sm.is_animating:
            return
        self._is_open = True
        self._entry_depth = self._sm.stack_depth
        if self._titlebar:
            self._titlebar.hide_custom_buttons()
        self._sm.push(self._build_menu(), AnimationType.SLIDE_LEFT)
        HookManager.instance().emit("on_settings_open")

    def close(self):
        if not self._is_open or self._sm.is_animating:
            return
        self._is_open = False
        if self._titlebar:
            self._titlebar.show_custom_buttons()
        # pop all intermediate settings pages instantly, animate the last one
        while self._sm.stack_depth > self._entry_depth + 1:
            old = self._sm._stack.pop()
            if self._sm._stack:
                self._sm._current = self._sm._stack[-1]
            if old:
                old.hide()
                old.setParent(None)
        self._sm.pop(AnimationType.SLIDE_RIGHT)
        HookManager.instance().emit("on_settings_close")

    def force_close(self):
        """Close all settings pages instantly."""
        if not self._is_open:
            return
        self._is_open = False
        if self._titlebar:
            self._titlebar.show_custom_buttons()
        # pop all settings scenes instantly
        while self._sm.stack_depth > self._entry_depth:
            if len(self._sm._stack) <= 1:
                break
            old = self._sm._stack.pop()
            if self._sm._stack:
                self._sm._current = self._sm._stack[-1]
                self._sm._current.show()
                self._sm._current.raise_()
            if old:
                old.hide()
                old.setParent(None)
        if self._sm._current:
            self._sm.scene_changed.emit(self._sm._current.name)

    def _reload_app(self):
        """Tell core to reload current app after language change."""
        from core.app import KislinkaApp
        app = KislinkaApp.instance()
        app._reload_current_app()

    def _register_core_tabs(self):
        self._pm.register_settings_tab(
            "core_themes", "themes", "settings",
            self._build_themes_page, owner=Permission.CORE,
        )
        self._pm.register_settings_tab(
            "core_language", "language", "settings",
            self._build_language_page, owner=Permission.CORE,
        )
        self._pm.register_settings_tab(
            "core_about", "about", "settings",
            self._build_about_page, owner=Permission.CORE,
        )

    # ── menu ────────────────────────────────────────

    def _build_menu(self) -> Scene:
        scene = Scene("settings_menu")
        lay = scene.scene_layout()
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        lay.addWidget(self._make_header(self._loc.t("settings"), on_back=self.close))

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(24, 24, 24, 24)
        cl.setSpacing(12)

        tabs = self._pm.get_settings_tabs()
        # filter: components can add/remove/reorder tabs
        tabs = HookManager.instance().filter("settings_tabs", tabs)
        for tab in tabs:
            builder = tab["builder"]
            display_name = self._loc.t(tab["name"], tab["name"])
            btn = KButton(display_name, on_click=self._make_tab_opener(builder))
            cl.addWidget(btn)

        cl.addStretch()
        scroll = KScrollArea()
        scroll.set_content(content)
        lay.addWidget(scroll, 1)
        return scene

    def _make_tab_opener(self, builder):
        def handler():
            if not self._sm.is_animating:
                self._sm.push(builder(), AnimationType.SLIDE_LEFT)
        return handler

    # ── themes ──────────────────────────────────────

    def _build_themes_page(self) -> Scene:
        scene = Scene("settings_themes")
        lay = scene.scene_layout()
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        lay.addWidget(self._make_header(self._loc.t("themes"), on_back=self._go_back))

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(24, 24, 24, 24)
        cl.setSpacing(20)

        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(8, 8, 8, 8)
        rl.addWidget(KLabel(self._loc.t("dark_mode"), style="body"))
        rl.addStretch()

        toggle = KToggle(checked=self._tm.is_dark)

        def on_toggle(checked):
            if checked != self._tm.is_dark:
                self._tm.toggle()
                self._storage.core_set("theme", "dark" if self._tm.is_dark else "light")

        toggle.toggled.connect(on_toggle)
        rl.addWidget(toggle)

        def sync():
            if sip_deleted(toggle):
                try:
                    self._tm.changed.disconnect(sync)
                except Exception:
                    pass
                return
            try:
                toggle._checked = self._tm.is_dark
                toggle._knob_x = toggle._knob_on_x() if toggle._checked else toggle._knob_off_x()
                toggle.update()
            except RuntimeError:
                try:
                    self._tm.changed.disconnect(sync)
                except Exception:
                    pass

        self._tm.changed.connect(sync)
        cl.addWidget(row)

        cl.addWidget(KLabel(self._loc.t("theme_description"), style="dim"))
        cl.addStretch()
        scroll = KScrollArea()
        scroll.set_content(content)
        lay.addWidget(scroll, 1)
        return scene

    # ── language ────────────────────────────────────

    def _build_language_page(self) -> Scene:
        scene = Scene("settings_language")
        lay = scene.scene_layout()
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        lay.addWidget(self._make_header(self._loc.t("language"), on_back=self._go_back))

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(24, 24, 24, 24)
        cl.setSpacing(8)

        # current status
        status_parts = []
        status_parts.append(f"Core: {self._loc.core_language}")
        status_parts.append(f"App: {self._loc.app_language}")
        cl.addWidget(KLabel(
            "  ·  ".join(status_parts),
            style="dim",
            align=Qt.AlignmentFlag.AlignCenter,
        ))
        cl.addSpacing(8)

        languages = self._loc.available_languages()

        for lang in languages:
            code = lang["code"]
            name = lang["name"]
            avail = lang["availability"]

            # build label with availability hint
            label = name
            if avail == "only_in_core":
                label += f"  {self._loc.t('only_in_core')}"
            elif avail == "only_in_app":
                label += f"  {self._loc.t('only_in_app')}"

            # is this the currently active language for both?
            is_current = (
                    code == self._loc.core_language
                    and code == self._loc.app_language
            )

            def make_handler(c):
                def handler():
                    self._storage.core_set("language", c)
                    self._loc.set_language(c)
                    self.force_close()
                    QTimer.singleShot(100, self._reload_app)

                return handler

            btn = KButton(label, on_click=make_handler(code))

            if is_current:
                btn.setEnabled(False)

            cl.addWidget(btn)

        cl.addStretch()
        scroll = KScrollArea()
        scroll.set_content(content)
        lay.addWidget(scroll, 1)
        return scene

    def _build_about_page(self) -> Scene:
        scene = Scene("settings_about")
        lay = scene.scene_layout()
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        lay.addWidget(self._make_header(self._loc.t("about"), on_back=self._go_back))

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(24, 30, 24, 24)
        cl.setSpacing(12)
        cl.setAlignment(Qt.AlignmentFlag.AlignTop)

        m = self._app_manifest
        if m:
            app_name = m.display_name
            info_lines = [
                (self._loc.t("application"), m.display_name),
                (self._loc.t("version"), m.version),
                (self._loc.t("author"), m.author),
            ]
        else:
            app_name = "KislinkaCore"
            info_lines = [(self._loc.t("application"), self._loc.t("no_app_loaded"))]

        cl.addWidget(KLabel(app_name, style="heading", align=Qt.AlignmentFlag.AlignCenter))
        cl.addSpacing(8)

        for label_text, value_text in info_lines:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(8, 4, 8, 4)
            rl.addWidget(KLabel(label_text, style="dim"))
            rl.addStretch()
            rl.addWidget(KLabel(value_text, style="body"))
            cl.addWidget(row)

        cl.addSpacing(20)

        btn_core = KButton(
            self._loc.t("about_the_core"),
            on_click=self._make_tab_opener(self._build_core_about_page),
        )
        cl.addWidget(btn_core)

        cl.addStretch()
        scroll = KScrollArea()
        scroll.set_content(content)
        lay.addWidget(scroll, 1)
        return scene

    # ── about the core ──────────────────────────────

    def _build_core_about_page(self) -> Scene:
        scene = Scene("settings_core_about")
        lay = scene.scene_layout()
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        lay.addWidget(self._make_header(self._loc.t("about_the_core"), on_back=self._go_back))

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(24, 30, 24, 24)
        cl.setSpacing(12)
        cl.setAlignment(Qt.AlignmentFlag.AlignTop)

        ci = self._core_info

        cl.addWidget(KLabel(
            ci.get("name", "KislinkaCore"),
            style="heading", align=Qt.AlignmentFlag.AlignCenter,
        ))
        cl.addSpacing(8)

        for label_key, value in [
            ("version", ci.get("version", "?")),
            ("author", ci.get("author", "?")),
            ("framework", ci.get("framework", "PyQt6")),
            ("description", ci.get("description", "")),
        ]:
            if not value:
                continue
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(8, 4, 8, 4)
            rl.addWidget(KLabel(self._loc.t(label_key), style="dim"))
            rl.addStretch()
            rl.addWidget(KLabel(value, style="body"))
            cl.addWidget(row)

        cl.addStretch()
        scroll = KScrollArea()
        scroll.set_content(content)
        lay.addWidget(scroll, 1)
        return scene

    # ── helpers ─────────────────────────────────────

    def _go_back(self):
        if not self._sm.is_animating:
            self._sm.pop(AnimationType.SLIDE_RIGHT)

    def _make_header(self, title: str, on_back=None) -> QWidget:
        header = QWidget()
        header.setFixedHeight(50)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(8, 0, 8, 0)
        hl.setSpacing(8)

        back_btn = QPushButton()
        back_btn.setFixedSize(36, 36)
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setIconSize(QSize(16, 16))
        if on_back:
            back_btn.clicked.connect(on_back)

        def style_back():
            try:
                if back_btn.isVisible() or not sip_deleted(back_btn):
                    t = self._tm
                    back_btn.setIcon(load_svg_icon("back", color=t.fg, size=16))
                    back_btn.setStyleSheet(f"""
                        QPushButton {{
                            background: transparent;
                            border: none;
                            border-radius: 6px;
                        }}
                        QPushButton:hover {{
                            background: {t.hover};
                        }}
                    """)
            except RuntimeError:
                pass

        style_back()
        self._tm.changed.connect(style_back)

        hl.addWidget(back_btn)

        title_label = KLabel(title, style="heading", font_size=18,
                             align=Qt.AlignmentFlag.AlignCenter)
        hl.addWidget(title_label, 1)
        hl.addSpacing(36)

        def style_header():
            try:
                if header.isVisible() or not sip_deleted(header):
                    t = self._tm
                    header.setStyleSheet(f"background: {t.bg}; border-bottom: 1px solid {t.hover};")
            except RuntimeError:
                pass

        style_header()
        self._tm.changed.connect(style_header)

        return header