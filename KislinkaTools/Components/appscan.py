from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from Components.paths import apps_dir


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


@dataclass
class AppInfo:
    name: str
    display_name: str
    entry_point: str
    main_class: str
    path: Path


def list_apps() -> list[AppInfo]:
    base = apps_dir()
    if not base.exists():
        return []

    apps: list[AppInfo] = []
    for folder in sorted(base.iterdir()):
        if not folder.is_dir():
            continue

        manifest_path = folder / "manifest.json"
        if not manifest_path.exists():
            continue

        data = _read_json(manifest_path)
        if not data:
            continue

        apps.append(
            AppInfo(
                name=str(data.get("name", folder.name)),
                display_name=str(data.get("display_name", data.get("name", folder.name))),
                entry_point=str(data.get("entry_point", "main.py")),
                main_class=str(data.get("main_class", "")),
                path=folder,
            )
        )

    return apps
