from __future__ import annotations

import json
from pathlib import Path

from Components.cli_utils import yes_no
from Components.i18n import I18n
from Components.paths import apps_dir


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def create_demo_app(i18n: I18n) -> None:
    base = apps_dir()
    base.mkdir(parents=True, exist_ok=True)

    app_dir = base / "KislinkaDemo"
    manifest_path = app_dir / "manifest.json"
    main_path = app_dir / "main.py"

    if app_dir.exists():
        if not yes_no(i18n.t("demo_exists"), default_yes=False):
            return

    app_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "name": "KislinkaDemo",
        "display_name": "KislinkaDemo",
        "version": "0.0.1",
        "author": "KislinkaTools",
        "main_class": "KislinkaDemo",
        "entry_point": "main.py",
        "window": {
            "width": 900,
            "height": 600
        }
    }
    _write_json(manifest_path, manifest)

    main_path.write_text(
        "from core.scene import Scene, AnimationType\n\n\nclass KislinkaDemo:\n    def setup(self, app):\n        self.app = app\n        self.sm = app.scene_manager\n\n        scene = Scene(\"demo\")\n        self.sm.push(scene, AnimationType.NONE)\n",
        encoding="utf-8",
    )

    print(i18n.t("demo_created"))
