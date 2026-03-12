"""KislinkaCore — Minimal B&W application framework."""

from core.hooks import HookManager
from core.component import KislinkaComponent
from core.component_manager import ComponentManager
from core.theme import ThemeManager, Theme, DARK, LIGHT
from core.fonts import Fonts
from core.app import KislinkaApp
from core.window import KislinkaWindow
from core.scene import Scene, SceneManager, AnimationType
from core.permissions import PermissionManager, Permission
from core.settings import SettingsPanel
from core.loader import AppLoader, AppManifest
from core.storage import StorageManager
from core.locale import LocaleManager
from core.error_handler import ErrorHandler, ErrorWindow
from core.launcher import LauncherWindow
from core.splash import SplashOverlay

__all__ = [
    "KislinkaApp", "KislinkaWindow",
    "ThemeManager", "Theme", "DARK", "LIGHT",
    "Fonts",
    "Scene", "SceneManager", "AnimationType",
    "PermissionManager", "Permission",
    "SettingsPanel",
    "AppLoader", "AppManifest",
    "StorageManager",
    "LocaleManager",
    "ErrorHandler", "ErrorWindow",
    "LauncherWindow",
    "SplashOverlay",
    "HookManager",
    "KislinkaComponent",
    "ComponentManager",
]