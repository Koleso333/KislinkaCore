from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from Components.paths import locales_dir


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


class I18n:
    def __init__(self, lang: str):
        self.lang = lang
        self._strings = _read_json(locales_dir() / f"{lang}.json")

    def t(self, key: str, fallback: str | None = None) -> str:
        if key in self._strings:
            return str(self._strings[key])
        return fallback if fallback is not None else key
