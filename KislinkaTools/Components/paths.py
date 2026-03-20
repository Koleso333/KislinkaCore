from __future__ import annotations

from pathlib import Path


def tools_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def root_dir() -> Path:
    return tools_dir().parent


def locales_dir() -> Path:
    return Path(__file__).resolve().parent / "locales"


def apps_dir() -> Path:
    return root_dir() / "App"


def components_dir() -> Path:
    return root_dir() / "components"


def assets_dir() -> Path:
    return root_dir() / "assets"


def cash_dir() -> Path:
    return tools_dir() / "Cash"


def buildcomplete_dir() -> Path:
    return tools_dir() / "BuildComplete"
