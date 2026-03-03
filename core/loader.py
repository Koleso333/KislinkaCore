"""
App loader.

Scans App/ directory for applications.
Each app has:
    App/<name>/manifest.json
    App/<name>/main.py (or custom entry_point)

Loader reads manifests, imports main classes, launches apps.
"""

import json
import importlib
import importlib.util
import sys
from pathlib import Path
from dataclasses import dataclass, field

from core.theme import ThemeManager


ROOT = Path(__file__).resolve().parent.parent
APPS_DIR = ROOT / "App"


def _log(msg: str):
    print(f"[Loader] {msg}")


@dataclass
class AppManifest:
    """Parsed manifest.json data."""
    name: str = ""
    display_name: str = ""
    version: str = "1.0.0"
    author: str = "Unknown"
    main_class: str = ""
    entry_point: str = "main.py"
    width: int = 900
    height: int = 600
    permissions: dict = field(default_factory=dict)
    settings_tabs: list = field(default_factory=list)
    path: Path = field(default_factory=Path)

    @classmethod
    def from_json(cls, json_path: Path) -> "AppManifest | None":
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception as e:
            _log(f"⚠ Failed to read {json_path}: {e}")
            return None

        window = data.get("window", {})

        return cls(
            name=data.get("name", json_path.parent.name),
            display_name=data.get("display_name", data.get("name", "Untitled")),
            version=data.get("version", "1.0.0"),
            author=data.get("author", "Unknown"),
            main_class=data.get("main_class", ""),
            entry_point=data.get("entry_point", "main.py"),
            width=window.get("width", 900),
            height=window.get("height", 600),
            permissions=data.get("permissions", {}),
            settings_tabs=data.get("settings_tabs", []),
            path=json_path.parent,
        )


class AppLoader:
    """Scans App/ and loads applications."""

    def __init__(self):
        self._manifests: list[AppManifest] = []
        self._loaded_app = None

    @property
    def manifests(self) -> list[AppManifest]:
        return self._manifests

    @property
    def loaded_app(self):
        return self._loaded_app

    def scan(self) -> list[AppManifest]:
        """Scan App/ directory for valid applications."""
        self._manifests.clear()

        if not APPS_DIR.exists():
            APPS_DIR.mkdir(parents=True, exist_ok=True)
            _log(f"Created App/ directory at {APPS_DIR}")
            return []

        for folder in sorted(APPS_DIR.iterdir()):
            if not folder.is_dir():
                continue
            manifest_path = folder / "manifest.json"
            if not manifest_path.exists():
                _log(f"⚠ Skipping {folder.name}: no manifest.json")
                continue

            manifest = AppManifest.from_json(manifest_path)
            if manifest is None:
                continue

            entry = folder / manifest.entry_point
            if not entry.exists():
                _log(f"⚠ Skipping {folder.name}: {manifest.entry_point} not found")
                continue

            _log(f"Found: {manifest.display_name} v{manifest.version} by {manifest.author}")
            self._manifests.append(manifest)

        _log(f"Total apps found: {len(self._manifests)}")
        return self._manifests

    def load_app(self, manifest: AppManifest):
        """
        Import the app module and instantiate the main class.
        Returns the app instance or None.
        """
        entry_file = manifest.path / manifest.entry_point

        try:
            # create unique module name
            module_name = f"kislinka_app_{manifest.name}"

            # add app directory to sys.path so relative imports work
            app_dir = str(manifest.path)
            if app_dir not in sys.path:
                sys.path.insert(0, app_dir)

            # load module from file
            spec = importlib.util.spec_from_file_location(
                module_name, str(entry_file)
            )
            if spec is None or spec.loader is None:
                _log(f"⚠ Cannot load {entry_file}")
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # get main class
            if not manifest.main_class:
                _log(f"⚠ No main_class in manifest for {manifest.name}")
                return None

            cls = getattr(module, manifest.main_class, None)
            if cls is None:
                _log(f"⚠ Class '{manifest.main_class}' not found in {entry_file}")
                return None

            # instantiate
            instance = cls()
            self._loaded_app = instance
            _log(f"Loaded: {manifest.display_name}")
            return instance

        except Exception as e:
            _log(f"⚠ Error loading {manifest.name}: {e}")
            import traceback
            traceback.print_exc()
            return None