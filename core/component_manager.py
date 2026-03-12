"""
Component manager — scans, loads, and manages lifecycle of components.

Components live in the components/ directory at project root.
Each component is a folder with manifest.json + entry point file.

Structure:
    components/
        MyComponent/
            manifest.json
            component.py       # (or custom entry_point)

manifest.json:
    {
        "name": "MyComponent",
        "display_name": "My Component",
        "version": "1.0.0",
        "author": "Author",
        "description": "What this component does",
        "main_class": "MyComponent",
        "entry_point": "component.py",
        "dependencies": [],
        "priority": 100
    }

Usage:
    # Core creates and manages ComponentManager automatically.
    # From apps:
    comp = app.components.get("MyComponent")
    comp.do_something()
"""

from __future__ import annotations

import json
import importlib.util
import sys
from pathlib import Path
from dataclasses import dataclass, field

from core.component import KislinkaComponent
from core.hooks import HookManager

from typing import Any


ROOT = Path(__file__).resolve().parent.parent
COMPONENTS_DIR = ROOT / "components"


def _log(msg: str) -> None:
    print(f"[Components] {msg}")


@dataclass
class ComponentManifest:
    """Parsed component manifest.json."""

    name: str = ""
    display_name: str = ""
    version: str = "1.0.0"
    author: str = "Unknown"
    description: str = ""
    main_class: str = ""
    entry_point: str = "component.py"
    dependencies: list[str] = field(default_factory=list)
    priority: int = 100
    path: Path = field(default_factory=Path)

    @classmethod
    def from_json(cls, json_path: Path) -> ComponentManifest | None:
        """Parse a manifest.json file. Returns None on failure."""
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception as exc:
            _log(f"⚠ Failed to read {json_path}: {exc}")
            return None

        return cls(
            name=data.get("name", json_path.parent.name),
            display_name=data.get("display_name", data.get("name", "Untitled")),
            version=data.get("version", "1.0.0"),
            author=data.get("author", "Unknown"),
            description=data.get("description", ""),
            main_class=data.get("main_class", ""),
            entry_point=data.get("entry_point", "component.py"),
            dependencies=data.get("dependencies", []),
            priority=data.get("priority", 100),
            path=json_path.parent,
        )


class ComponentManager:
    """
    Singleton component manager.

    Lifecycle:
        scan()            — find components in components/ directory
        load_all(core)    — import, instantiate, call on_register(core)
        notify_ready()    — call on_ready() on all components
        notify_app_setup(app)  — call on_app_setup(app) on all
        notify_app_cleanup()   — call on_app_cleanup() on all
        unload_all()      — call on_unload(), clean up hooks
    """

    _instance: ComponentManager | None = None

    def __init__(self) -> None:
        if ComponentManager._instance is not None:
            raise RuntimeError("Use ComponentManager.instance()")
        ComponentManager._instance = self

        self._manifests: list[ComponentManifest] = []
        self._components: dict[str, KislinkaComponent] = {}  # name → instance
        self._load_order: list[str] = []  # names in load order
        self._services: dict[str, Any] = {}    # service registry
        self._widgets: dict[str, type] = {}    # widget class registry
        self._core = None

    @classmethod
    def instance(cls) -> ComponentManager:
        if cls._instance is None:
            cls()
        return cls._instance

    # ── scanning ────────────────────────────────────

    def scan(self) -> list[ComponentManifest]:
        """Scan components/ directory for valid components."""
        self._manifests.clear()

        if not COMPONENTS_DIR.exists():
            COMPONENTS_DIR.mkdir(parents=True, exist_ok=True)
            _log(f"Created components/ directory at {COMPONENTS_DIR}")
            return []

        for folder in sorted(COMPONENTS_DIR.iterdir()):
            if not folder.is_dir():
                continue

            # skip hidden / __pycache__
            if folder.name.startswith((".", "_")):
                continue

            manifest_path = folder / "manifest.json"
            if not manifest_path.exists():
                _log(f"⚠ Skipping {folder.name}: no manifest.json")
                continue

            manifest = ComponentManifest.from_json(manifest_path)
            if manifest is None:
                continue

            entry = folder / manifest.entry_point
            if not entry.exists():
                _log(f"⚠ Skipping {folder.name}: {manifest.entry_point} not found")
                continue

            if not manifest.main_class:
                _log(f"⚠ Skipping {folder.name}: no main_class in manifest")
                continue

            _log(f"Found: {manifest.display_name} v{manifest.version}")
            self._manifests.append(manifest)

        # sort by priority (lower = loaded first)
        self._manifests.sort(key=lambda m: m.priority)

        _log(f"Total components found: {len(self._manifests)}")
        return self._manifests

    # ── loading ─────────────────────────────────────

    def load_all(self, core) -> None:
        """
        Load all scanned components: import modules, instantiate classes,
        resolve dependencies, call on_register(core).
        """
        self._core = core

        if not self._manifests:
            return

        # check dependencies before loading
        available = {m.name for m in self._manifests}
        for manifest in self._manifests:
            for dep in manifest.dependencies:
                if dep not in available:
                    _log(
                        f"⚠ {manifest.name} requires '{dep}' — "
                        f"not found, skipping"
                    )
                    self._manifests = [
                        m for m in self._manifests if m.name != manifest.name
                    ]
                    break

        # load in priority order
        for manifest in self._manifests:
            instance = self._load_one(manifest)
            if instance is None:
                continue

            self._components[manifest.name] = instance
            self._load_order.append(manifest.name)

            # call on_register
            try:
                instance.on_register(core)
                _log(f"Registered: {manifest.display_name}")
            except Exception as exc:
                _log(f"⚠ on_register error for {manifest.name}: {exc}")
                import traceback
                traceback.print_exc()

    def _load_one(self, manifest: ComponentManifest) -> KislinkaComponent | None:
        """Import module and instantiate main class."""
        entry_file = manifest.path / manifest.entry_point

        try:
            module_name = f"kislinka_component_{manifest.name}"

            # add component directory to sys.path
            comp_dir = str(manifest.path)
            if comp_dir not in sys.path:
                sys.path.insert(0, comp_dir)

            spec = importlib.util.spec_from_file_location(
                module_name, str(entry_file),
            )
            if spec is None or spec.loader is None:
                _log(f"⚠ Cannot create spec for {entry_file}")
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            cls = getattr(module, manifest.main_class, None)
            if cls is None:
                _log(
                    f"⚠ Class '{manifest.main_class}' not found "
                    f"in {entry_file}"
                )
                return None

            instance = cls()

            # verify it's a KislinkaComponent (or duck-types enough)
            if not isinstance(instance, KislinkaComponent):
                _log(
                    f"⚠ {manifest.main_class} does not extend "
                    f"KislinkaComponent — loading anyway"
                )

            _log(f"Loaded: {manifest.display_name}")
            return instance

        except Exception as exc:
            _log(f"⚠ Error loading {manifest.name}: {exc}")
            import traceback
            traceback.print_exc()
            return None

    # ── lifecycle notifications ─────────────────────

    def notify_ready(self) -> None:
        """Call on_ready() on all loaded components."""
        for name in self._load_order:
            comp = self._components.get(name)
            if comp is None:
                continue
            try:
                comp.on_ready()
            except Exception as exc:
                _log(f"⚠ on_ready error for {name}: {exc}")

        if self._components:
            _log(f"All components ready ({len(self._components)})")

    def notify_app_setup(self, app_instance) -> None:
        """Call on_app_setup() on all components after user app setup."""
        for name in self._load_order:
            comp = self._components.get(name)
            if comp is None:
                continue
            try:
                comp.on_app_setup(app_instance)
            except Exception as exc:
                _log(f"⚠ on_app_setup error for {name}: {exc}")

    def notify_app_cleanup(self) -> None:
        """Call on_app_cleanup() on all components before user app cleanup."""
        for name in self._load_order:
            comp = self._components.get(name)
            if comp is None:
                continue
            try:
                comp.on_app_cleanup()
            except Exception as exc:
                _log(f"⚠ on_app_cleanup error for {name}: {exc}")

    def unload_all(self) -> None:
        """Unload all components (shutdown)."""
        hooks = HookManager.instance()

        # unload in reverse order
        for name in reversed(self._load_order):
            comp = self._components.get(name)
            if comp is None:
                continue
            try:
                comp.on_unload()
            except Exception as exc:
                _log(f"⚠ on_unload error for {name}: {exc}")

            # auto-unregister all hooks owned by this component
            hooks.unregister_owner(name)

        self._components.clear()
        self._load_order.clear()
        self._manifests.clear()
        _log("All components unloaded")

    # ── access API ──────────────────────────────────

    def get(self, name: str) -> KislinkaComponent | None:
        """Get a loaded component by name."""
        return self._components.get(name)

    def get_all(self) -> dict[str, KislinkaComponent]:
        """Get all loaded components (name → instance)."""
        return dict(self._components)

    def has(self, name: str) -> bool:
        """Check if a component is loaded."""
        return name in self._components

    def names(self) -> list[str]:
        """List loaded component names (in load order)."""
        return list(self._load_order)

    @property
    def manifests(self) -> list[ComponentManifest]:
        """All scanned manifests."""
        return list(self._manifests)

    @property
    def count(self) -> int:
        """Number of loaded components."""
        return len(self._components)

    # ── service registry ────────────────────────────

    def register_service(self, name: str, instance: Any) -> None:
        """
        Register a named service that other components and apps can access.

        Example:
            # in component:
            core.components.register_service("http", MyHttpClient())

            # in app:
            http = app.components.get_service("http")
            http.get("https://...")
        """
        if name in self._services:
            _log(f"⚠ Service '{name}' already registered — overwriting")
        self._services[name] = instance
        _log(f"Service registered: {name}")

    def get_service(self, name: str) -> Any | None:
        """Get a registered service by name."""
        return self._services.get(name)

    def has_service(self, name: str) -> bool:
        """Check if a service is registered."""
        return name in self._services

    def list_services(self) -> list[str]:
        """List all registered service names."""
        return sorted(self._services.keys())

    def unregister_service(self, name: str) -> bool:
        """Remove a service."""
        if name in self._services:
            del self._services[name]
            return True
        return False

    # ── widget registry ─────────────────────────────

    def register_widget(self, name: str, widget_class: type) -> None:
        """
        Register a widget class that apps can instantiate.

        Example:
            # in component:
            core.components.register_widget("ColorPicker", ColorPickerWidget)

            # in app:
            ColorPicker = app.components.get_widget("ColorPicker")
            picker = ColorPicker(parent=some_widget)
        """
        if name in self._widgets:
            _log(f"⚠ Widget '{name}' already registered — overwriting")
        self._widgets[name] = widget_class
        _log(f"Widget registered: {name}")

    def get_widget(self, name: str) -> type | None:
        """Get a registered widget class by name."""
        return self._widgets.get(name)

    def has_widget(self, name: str) -> bool:
        """Check if a widget class is registered."""
        return name in self._widgets

    def list_widgets(self) -> list[str]:
        """List all registered widget names."""
        return sorted(self._widgets.keys())

    # ── component storage (scoped) ──────────────────

    def storage_set(self, component_name: str, key: str, value: Any) -> None:
        """Save data scoped to a component."""
        from core.storage import StorageManager
        st = StorageManager.instance()
        st.component_set(component_name, key, value)

    def storage_get(self, component_name: str, key: str, default: Any = None) -> Any:
        """Read data scoped to a component."""
        from core.storage import StorageManager
        st = StorageManager.instance()
        return st.component_get(component_name, key, default)

    def storage_delete(self, component_name: str, key: str) -> None:
        """Delete data scoped to a component."""
        from core.storage import StorageManager
        st = StorageManager.instance()
        st.component_delete(component_name, key)
