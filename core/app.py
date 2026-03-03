"""
KislinkaApp — root controller with error handling, launcher, splash.
"""

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer

from core.theme import ThemeManager
from core.fonts import load_fonts
from core.window import KislinkaWindow
from core.scene import SceneManager, Scene, AnimationType
from core.permissions import PermissionManager
from core.settings import SettingsPanel
from core.loader import AppLoader, AppManifest
from core.storage import StorageManager
from core.locale import LocaleManager
from core.error_handler import ErrorHandler, KislinkaQApplication
from core.launcher import LauncherWindow
from core.splash import SplashOverlay
from audio.player import AudioPlayer


ROOT   = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"


def _log(msg: str) -> None:
    print(f"[KislinkaCore] {msg}")


class KislinkaApp:

    _instance: "KislinkaApp | None" = None

    def __init__(self) -> None:
        if KislinkaApp._instance is not None:
            raise RuntimeError("KislinkaApp already created")
        KislinkaApp._instance = self

        # use custom QApplication that catches exceptions in slots
        self._qt = KislinkaQApplication(sys.argv)
        self._qt.setApplicationName("KislinkaCore")
        self._qt.setQuitOnLastWindowClosed(False)

        # install error handler
        ErrorHandler.install()

        self._theme = ThemeManager.instance()
        self._permissions = PermissionManager.instance()
        self._storage = StorageManager.instance()
        self._locale = LocaleManager.instance()
        self._audio = AudioPlayer.instance()
        self._loader = AppLoader()

        load_fonts()

        saved_theme = self._storage.core_get("theme", "dark")
        self._theme.set_theme(saved_theme)

        saved_lang = self._storage.core_get("language", "en")
        self._locale.set_language(saved_lang)

        self._apply_theme()
        self._theme.changed.connect(self._apply_theme)

        self._window: KislinkaWindow | None = None
        self._scene_manager: SceneManager | None = None
        self._settings: SettingsPanel | None = None
        self._splash: SplashOverlay | None = None
        self._launcher: LauncherWindow | None = None
        self._current_app = None
        self._current_manifest: AppManifest | None = None
        self._pending_manifest: AppManifest | None = None

        _log("Core initialised ✓")

    @classmethod
    def instance(cls) -> "KislinkaApp":
        if cls._instance is None:
            raise RuntimeError("KislinkaApp not created yet")
        return cls._instance

    @property
    def theme_manager(self) -> ThemeManager:
        return self._theme

    @property
    def window(self) -> KislinkaWindow | None:
        return self._window

    @property
    def scene_manager(self) -> SceneManager | None:
        return self._scene_manager

    @property
    def settings(self) -> SettingsPanel | None:
        return self._settings

    @property
    def permissions(self) -> PermissionManager:
        return self._permissions

    @property
    def audio(self) -> AudioPlayer:
        return self._audio

    @property
    def storage(self) -> StorageManager:
        return self._storage

    @property
    def locale(self) -> LocaleManager:
        return self._locale

    @property
    def qt(self) -> QApplication:
        return self._qt

    def _apply_theme(self) -> None:
        self._qt.setStyleSheet(self._theme.base_qss())

    def _toggle_settings(self):
        if self._settings.is_open:
            self._settings.close()
        else:
            self._settings.open()

    def run(self) -> None:
        manifests = self._loader.scan()

        if len(manifests) == 0:
            self._show_no_apps_error()
        elif len(manifests) == 1:
            self._start_single_app(manifests[0])
        else:
            self._start_launcher(manifests)

        exit_code = self._qt.exec()
        self._audio.shutdown()
        sys.exit(exit_code)

    # ── No apps → Error ─────────────────────────────

    def _show_no_apps_error(self):
        ErrorHandler.show_error(
            "No Applications Found",
            "Create a folder in App/ with manifest.json and main.py",
            "KislinkaCore requires at least one application to run.\n\n"
            "Structure:\n"
            "  App/\n"
            "    YourApp/\n"
            "      manifest.json\n"
            "      main.py\n"
        )

    # ── Single app — window with splash ─────────────

    # ── Single app — window with splash ─────────────

    def _start_single_app(self, manifest: AppManifest):
        self._pending_manifest = manifest

        # create window
        self._create_window(manifest.display_name, manifest.width, manifest.height)

        # splash covers ENTIRE window (parent = window, not body)
        self._splash = SplashOverlay(self._window, manifest.display_name)

        # show window
        self._window.show()

        # load app after delay
        QTimer.singleShot(150, self._load_pending_app)

    def _load_pending_app(self):
        manifest = self._pending_manifest
        if not manifest:
            return

        self._setup_app(manifest)

        # animate splash out
        QTimer.singleShot(100, self._finish_splash)

    def _finish_splash(self):
        if self._splash:
            self._splash.finish()
            self._splash = None

    # ── Multiple apps — show launcher ───────────────

    def _start_launcher(self, manifests: list[AppManifest]):
        self._launcher = LauncherWindow(manifests)
        self._launcher.app_selected.connect(self._on_launcher_select)
        self._launcher.closed_without_selection.connect(self._on_launcher_closed)
        self._launcher.show()

    def _on_launcher_select(self, manifest: AppManifest):
        self._pending_manifest = manifest

        if self._launcher:
            self._launcher.hide()

        # create window
        self._create_window(manifest.display_name, manifest.width, manifest.height)

        # splash covers ENTIRE window
        self._splash = SplashOverlay(self._window, manifest.display_name)

        self._window.show()

        if self._launcher:
            self._launcher._selected = True
            self._launcher.close()
            self._launcher = None

        QTimer.singleShot(150, self._load_pending_app)

    def _on_launcher_closed(self):
        self._launcher = None
        QApplication.quit()

    def _reload_current_app(self):
        """Reload current app (used after language change)."""
        if not self._current_app or not self._current_manifest:
            return

        manifest = self._current_manifest

        # cleanup old app
        if hasattr(self._current_app, "cleanup"):
            try:
                self._current_app.cleanup()
            except Exception as e:
                _log(f"⚠ Cleanup error: {e}")

        self._current_app = None

        # clear titlebar custom buttons
        self._window.titlebar.clear_custom_buttons()

        # DISCONNECT ALL theme signals from old widgets
        # (prevents crashes when deleted widgets get theme updates)
        self._theme.changed.disconnect()
        # reconnect core's own theme handler
        self._theme.changed.connect(self._apply_theme)

        # hide and remove all scenes
        for scene in self._scene_manager._stack:
            scene.hide()
            scene.setParent(None)
        self._scene_manager._stack.clear()
        self._scene_manager._current = None

        # remove scene manager from body
        self._window.body_layout.removeWidget(self._scene_manager)
        self._scene_manager.setParent(None)
        self._scene_manager.deleteLater()

        # create fresh scene manager
        self._scene_manager = SceneManager(self._window.body)
        self._window.body_layout.addWidget(self._scene_manager)

        # reconnect settings to new scene manager
        self._settings = SettingsPanel(self._scene_manager)
        self._settings.set_titlebar(self._window.titlebar)
        self._settings.set_app_manifest(manifest)

        try:
            self._window.titlebar.settings_clicked.disconnect()
        except Exception:
            pass
        self._window.titlebar.settings_clicked.connect(self._toggle_settings)

        # re-apply theme to window
        self._window._apply_theme()
        self._theme.changed.connect(self._window._apply_theme)

        # re-apply theme to entire titlebar (including all buttons)
        self._window.titlebar.reconnect_theme()

        # reload locales
        self._locale.load_app_locales(manifest.path)

        # remove cached module
        module_name = f"kislinka_app_{manifest.name}"
        if module_name in sys.modules:
            del sys.modules[module_name]

        # load app fresh
        app_instance = self._loader.load_app(manifest)
        if app_instance is None:
            _log("⚠ Failed to reload app")
            return

        self._current_app = app_instance

        try:
            app_instance.setup(self)
            _log(f"App reloaded: {manifest.display_name}")
        except Exception as e:
            _log(f"⚠ App reload error: {e}")
            import traceback
            traceback.print_exc()
            raise

    # ── Window creation ─────────────────────────────

    def _create_window(self, title: str, width: int, height: int):
        self._window = KislinkaWindow(title, width, height)
        self._window.center_on_screen()

        self._scene_manager = SceneManager(self._window.body)
        self._window.body_layout.addWidget(self._scene_manager)

        self._settings = SettingsPanel(self._scene_manager)
        self._settings.set_titlebar(self._window.titlebar)
        self._window.titlebar.settings_clicked.connect(self._toggle_settings)

    # ── App setup ───────────────────────────────────

    def _setup_app(self, manifest: AppManifest):
        _log(f"Setting up: {manifest.display_name}")

        self._settings.set_app_manifest(manifest)
        self._locale.load_app_locales(manifest.path)
        self._storage.set_app(manifest.name)

        app_instance = self._loader.load_app(manifest)
        if app_instance is None:
            _log("⚠ Failed to load app")
            ErrorHandler.show_error(
                "Failed to Load Application",
                f"Could not load {manifest.display_name}",
                "Check console for details."
            )
            return

        self._current_app = app_instance
        self._current_manifest = manifest

        app_instance.setup(self)