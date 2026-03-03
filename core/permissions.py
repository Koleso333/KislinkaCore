"""
Permission system.
"""

from enum import Enum, auto
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QObject, pyqtSignal


class Permission(Enum):
    CORE = auto()
    APP  = auto()
    USER = auto()


class PermissionManager(QObject):

    widget_state_changed = pyqtSignal(str, bool)
    _instance: "PermissionManager | None" = None

    _ALLOWED_ACTIONS = {
        Permission.CORE: {
            "add_settings_tab", "remove_settings_tab",
            "modify_core_tabs", "change_window_size", "toggle_theme",
        },
        Permission.APP: {
            "add_settings_tab", "disable_widget",
            "enable_widget", "change_window_size", "toggle_theme",
        },
        Permission.USER: {"toggle_theme"},
    }

    def __init__(self):
        if PermissionManager._instance is not None:
            raise RuntimeError("Use PermissionManager.instance()")
        super().__init__()
        self._widgets: dict[str, dict] = {}
        self._settings_tabs: dict[str, dict] = {}
        PermissionManager._instance = self

    @classmethod
    def instance(cls) -> "PermissionManager":
        if cls._instance is None:
            cls()
        return cls._instance

    def is_allowed(self, level: Permission, action: str) -> bool:
        return action in self._ALLOWED_ACTIONS.get(level, set())

    def register_widget(self, widget_id: str, widget: QWidget, owner: Permission = Permission.APP):
        self._widgets[widget_id] = {"widget": widget, "owner": owner, "enabled": widget.isEnabled()}

    def set_enabled(self, widget_id: str, enabled: bool, caller: Permission = Permission.APP):
        if widget_id not in self._widgets:
            return
        entry = self._widgets[widget_id]
        if entry["owner"] == Permission.CORE and caller != Permission.CORE:
            return
        entry["enabled"] = enabled
        entry["widget"].setEnabled(enabled)
        self.widget_state_changed.emit(widget_id, enabled)

    def get_widget(self, widget_id: str) -> QWidget | None:
        entry = self._widgets.get(widget_id)
        return entry["widget"] if entry else None

    def register_settings_tab(self, tab_id: str, name: str, icon_name: str, scene_builder, owner: Permission = Permission.APP):
        self._settings_tabs[tab_id] = {"name": name, "icon": icon_name, "builder": scene_builder, "owner": owner}

    def remove_settings_tab(self, tab_id: str, caller: Permission = Permission.APP):
        if tab_id not in self._settings_tabs:
            return False
        if self._settings_tabs[tab_id]["owner"] == Permission.CORE and caller != Permission.CORE:
            return False
        del self._settings_tabs[tab_id]
        return True

    def get_settings_tabs(self) -> list[dict]:
        core, app = [], []
        for tab_id, info in self._settings_tabs.items():
            entry = {"id": tab_id, **info}
            (core if info["owner"] == Permission.CORE else app).append(entry)
        return core + app