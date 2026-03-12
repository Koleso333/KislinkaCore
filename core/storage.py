"""
Data storage for core, apps, and components.

Core data:       %LOCALAPPDATA%/KislinkaCore/core_settings.json
App data:        %LOCALAPPDATA%/KislinkaCore/<appname>/app_data.json
Component data:  %LOCALAPPDATA%/KislinkaCore/_components/<compname>/data.json

Usage:
    storage = StorageManager.instance()

    # core settings
    storage.core_set("theme", "dark")
    theme = storage.core_get("theme", "dark")

    # app data
    storage.set_app("MyApp")
    storage.app_set("username", "Kislinka")
    name = storage.app_get("username", "")
"""

import json
import os
from pathlib import Path
from PyQt6.QtCore import QObject


def _log(msg: str):
    print(f"[Storage] {msg}")


def _get_base_dir() -> Path:
    """Get base storage directory."""
    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        base = Path(local) / "KislinkaCore"
    else:
        base = Path.home() / ".kislinka_core"
    return base


class StorageManager(QObject):
    """Singleton storage manager."""

    _instance: "StorageManager | None" = None

    def __init__(self):
        if StorageManager._instance is not None:
            raise RuntimeError("Use StorageManager.instance()")
        super().__init__()
        StorageManager._instance = self

        self._base_dir = _get_base_dir()
        self._core_file = self._base_dir / "core_settings.json"
        self._core_data: dict = {}

        self._app_name: str = ""
        self._app_file: Path | None = None
        self._app_data: dict = {}

        self._comp_cache: dict[str, dict] = {}  # component_name → data
        self._comp_dir = self._base_dir / "_components"

        # ensure base dir
        self._base_dir.mkdir(parents=True, exist_ok=True)

        # load core
        self._core_data = self._load_file(self._core_file)
        _log(f"Storage dir: {self._base_dir}")

    @classmethod
    def instance(cls) -> "StorageManager":
        if cls._instance is None:
            cls()
        return cls._instance

    # ── core settings ───────────────────────────────

    def core_get(self, key: str, default=None):
        return self._core_data.get(key, default)

    def core_set(self, key: str, value):
        self._core_data[key] = value
        self._save_file(self._core_file, self._core_data)

    def core_delete(self, key: str):
        if key in self._core_data:
            del self._core_data[key]
            self._save_file(self._core_file, self._core_data)

    def core_get_all(self) -> dict:
        return dict(self._core_data)

    # ── app data ────────────────────────────────────

    def set_app(self, app_name: str):
        """Set current app for data storage."""
        self._app_name = app_name
        app_dir = self._base_dir / app_name
        app_dir.mkdir(parents=True, exist_ok=True)
        self._app_file = app_dir / "app_data.json"
        self._app_data = self._load_file(self._app_file)
        _log(f"App storage: {self._app_file}")

    def app_get(self, key: str, default=None):
        return self._app_data.get(key, default)

    def app_set(self, key: str, value):
        self._app_data[key] = value
        if self._app_file:
            self._save_file(self._app_file, self._app_data)

    def app_delete(self, key: str):
        if key in self._app_data:
            del self._app_data[key]
            if self._app_file:
                self._save_file(self._app_file, self._app_data)

    def app_get_all(self) -> dict:
        return dict(self._app_data)

    def app_clear(self):
        self._app_data.clear()
        if self._app_file:
            self._save_file(self._app_file, self._app_data)

    # ── component data ───────────────────────────────

    def _comp_file(self, comp_name: str) -> Path:
        return self._comp_dir / comp_name / "data.json"

    def _ensure_comp_loaded(self, comp_name: str) -> dict:
        if comp_name not in self._comp_cache:
            self._comp_cache[comp_name] = self._load_file(self._comp_file(comp_name))
        return self._comp_cache[comp_name]

    def component_get(self, comp_name: str, key: str, default=None):
        """Read component-scoped data."""
        data = self._ensure_comp_loaded(comp_name)
        return data.get(key, default)

    def component_set(self, comp_name: str, key: str, value):
        """Write component-scoped data."""
        data = self._ensure_comp_loaded(comp_name)
        data[key] = value
        self._save_file(self._comp_file(comp_name), data)

    def component_delete(self, comp_name: str, key: str):
        """Delete a key from component-scoped data."""
        data = self._ensure_comp_loaded(comp_name)
        if key in data:
            del data[key]
            self._save_file(self._comp_file(comp_name), data)

    def component_get_all(self, comp_name: str) -> dict:
        """Get all data for a component."""
        return dict(self._ensure_comp_loaded(comp_name))

    def component_clear(self, comp_name: str):
        """Clear all data for a component."""
        self._comp_cache[comp_name] = {}
        self._save_file(self._comp_file(comp_name), {})

    # ── file I/O ────────────────────────────────────

    def _load_file(self, path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            text = path.read_text(encoding="utf-8")
            data = json.loads(text)
            return data if isinstance(data, dict) else {}
        except Exception as e:
            _log(f"⚠ Load error {path.name}: {e}")
            return {}

    def _save_file(self, path: Path, data: dict):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            _log(f"⚠ Save error {path.name}: {e}")