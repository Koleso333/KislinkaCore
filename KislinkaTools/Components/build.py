from __future__ import annotations

import hashlib
import io
import json
import importlib
import os
import re
import shutil
import struct
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from Components.appscan import AppInfo
from Components.cli_utils import run_silent_with_spinner
from Components.i18n import I18n
from Components.paths import assets_dir, components_dir, root_dir, apps_dir, cash_dir, buildcomplete_dir


# Hidden imports that PyInstaller cannot auto-detect for the audio
# backend (PyAV + sounddevice).  These ensure the bundled FFmpeg libs
# and PortAudio binary are included in the final executable.
_CORE_HIDDEN_IMPORTS: list[str] = [
    "av",
    "av.audio",
    "av.audio.frame",
    "av.audio.resampler",
    "av.container",
    "av.format",
    "av.stream",
    "av.codec",
    "av.packet",
    "sounddevice",
    "_sounddevice_data",
    "numpy",
    "numpy.core",
    "numpy.core._methods",
    "numpy.core._dtype_ctypes",
]


def _png_to_ico(png_path: Path, ico_path: Path) -> bool:
    """Convert PNG to ICO with multiple sizes. Returns True on success."""
    try:
        from PIL import Image
    except ImportError:
        print(f"[KislinkaTools] Pillow not available, cannot convert {png_path} to ICO")
        return False

    try:
        img = Image.open(png_path)
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        
        # Use Pillow's native ICO saving with BMP format (Windows compatible)
        try:
            img.save(ico_path, format="ICO", sizes=sizes, bitmap_format="bmp")
        except TypeError:
            # Older Pillow versions don't support bitmap_format
            img.save(ico_path, format="ICO", sizes=sizes)
        
        print(f"[KislinkaTools] Converted {png_path.name} -> {ico_path.name} ({ico_path.stat().st_size} bytes)")
        return True
    except Exception as e:
        print(f"[KislinkaTools] Failed to convert {png_path} to ICO: {e}")
        return False


def _get_cached_ico_for_png(png_path: Path) -> Path | None:
    """Convert PNG to ICO and cache it. Returns path to ICO or None."""
    cache_dir = cash_dir() / "icon_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Use hash of PNG path + mtime for cache key
    try:
        mtime = png_path.stat().st_mtime
    except OSError:
        mtime = 0
    key = hashlib.md5(f"{png_path}:{mtime}".encode()).hexdigest()
    ico_path = cache_dir / f"{key}.ico"

    if ico_path.exists():
        return ico_path

    if _png_to_ico(png_path, ico_path):
        return ico_path
    return None


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _parse_component_manifest(path: Path) -> dict[str, Any]:
    manifest_path = path / "manifest.json"
    if not manifest_path.exists():
        return {}
    return _read_json(manifest_path)


def _get_component_folder_by_name(comp_name: str) -> Path | None:
    cdir = components_dir()
    src = cdir / comp_name
    if src.exists() and src.is_dir():
        return src

    if cdir.exists():
        for folder in cdir.iterdir():
            if not folder.is_dir():
                continue
            data = _parse_component_manifest(folder)
            if str(data.get("name", "")) == comp_name:
                return folder

    return None


def _collect_hidden_imports_from_component_folder(folder: Path) -> list[str]:
    data = _parse_component_manifest(folder)
    raw = data.get("hidden_imports", [])
    if not isinstance(raw, list):
        return []
    result: list[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            result.append(item.strip())
    return result


def _validate_hidden_imports(mods: list[str]) -> None:
    # Best-effort validation in build environment so user gets an early signal.
    for m in mods:
        try:
            importlib.import_module(m)
        except Exception as exc:
            print(f"[KislinkaTools] ⚠ hidden_import '{m}' is not importable in build env: {exc}")


_COMPONENT_USAGE_PATTERNS: list[re.Pattern[str]] = [
    # Direct: components.get("Name")
    re.compile(r"components\.get\(\s*['\"]([A-Za-z0-9_\-]+)['\"]\s*\)"),
    re.compile(r"components\.has\(\s*['\"]([A-Za-z0-9_\-]+)['\"]\s*\)"),
    re.compile(r"components\.get_service\(\s*['\"]([A-Za-z0-9_\-]+)['\"]\s*\)"),
    re.compile(r"components\.get_widget\(\s*['\"]([A-Za-z0-9_\-]+)['\"]\s*\)"),
    # Via app/self: app.components.get("Name"), self.components.get("Name")
    re.compile(r"\.components\.get\(\s*['\"]([A-Za-z0-9_\-]+)['\"]\s*\)"),
    re.compile(r"\.components\.has\(\s*['\"]([A-Za-z0-9_\-]+)['\"]\s*\)"),
    re.compile(r"\.components\.get_service\(\s*['\"]([A-Za-z0-9_\-]+)['\"]\s*\)"),
    re.compile(r"\.components\.get_widget\(\s*['\"]([A-Za-z0-9_\-]+)['\"]\s*\)"),
]


def detect_used_components(app_dir: Path) -> set[str]:
    used: set[str] = set()

    if not app_dir.exists():
        return used

    for py in app_dir.rglob("*.py"):
        try:
            txt = py.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for pat in _COMPONENT_USAGE_PATTERNS:
            for m in pat.finditer(txt):
                used.add(m.group(1))

    print(f"[KislinkaTools] Detected components: {sorted(used) if used else 'none'}")
    return used


def resolve_component_deps(component_names: set[str]) -> set[str]:
    resolved = set(component_names)

    manifests: dict[str, list[str]] = {}
    cdir = components_dir()
    if cdir.exists():
        for folder in cdir.iterdir():
            if not folder.is_dir() or folder.name.startswith((".", "_")):
                continue
            data = _parse_component_manifest(folder)
            name = str(data.get("name", folder.name))
            deps = data.get("dependencies", [])
            if isinstance(deps, list):
                manifests[name] = [str(d) for d in deps]

    changed = True
    while changed:
        changed = False
        for name in list(resolved):
            for dep in manifests.get(name, []):
                if dep and dep not in resolved:
                    resolved.add(dep)
                    changed = True

    return resolved


def _run_pyinstaller(
    i18n: I18n,
    *,
    name: str,
    entry_script: Path,
    add_data: list[tuple[Path, str]],
    icon_path: Path | None = None,
    hidden_imports: list[str] | None = None,
) -> None:
    if not entry_script.exists():
        print(i18n.t("entry_not_found"), str(entry_script))
        raise FileNotFoundError(str(entry_script))

    sep = ";" if os.name == "nt" else ":"

    cmd: list[str] = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--noconsole",
        "--name",
        name,
        "--paths",
        str(root_dir()),
    ]

    out_dir = buildcomplete_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Rename existing exe with same name instead of deleting
    existing_exe = out_dir / f"{name}.exe"
    if existing_exe.exists():
        # Find next available suffix
        suffix = 1
        while True:
            renamed = out_dir / f"{name} ({suffix}).exe"
            if not renamed.exists():
                break
            suffix += 1
        try:
            existing_exe.rename(renamed)
            print(f"[KislinkaTools] Renamed old exe: {existing_exe.name} -> {renamed.name}")
        except Exception:
            pass

    cmd += ["--distpath", str(out_dir)]

    cash = cash_dir()
    cash.mkdir(parents=True, exist_ok=True)
    build_cash = cash / f"build_{name}_{int(time.time())}"
    workpath = build_cash / "pyi_work"
    specpath = build_cash / "pyi_spec"
    workpath.mkdir(parents=True, exist_ok=True)
    specpath.mkdir(parents=True, exist_ok=True)
    cmd += ["--workpath", str(workpath), "--specpath", str(specpath)]

    if icon_path is not None and icon_path.exists():
        cmd += ["--icon", str(icon_path)]
        print(f"[KislinkaTools] PyInstaller icon: {icon_path}")

    if hidden_imports:
        for mod in hidden_imports:
            if mod:
                cmd += ["--hidden-import", mod]

    for src, dest in add_data:
        cmd += ["--add-data", f"{src}{sep}{dest}"]

    cmd.append(str(entry_script))

    try:
        run_silent_with_spinner(cmd, cwd=str(root_dir()), show_last_line=True)
    except subprocess.CalledProcessError as exc:
        print(i18n.t("build_failed"), str(exc))
        raise
    finally:
        if build_cash.exists():
            shutil.rmtree(build_cash, ignore_errors=True)


def _resolve_app_icon_for_build(app: AppInfo) -> Path | None:
    """Resolve icon for build. Converts PNG to ICO for reliable Windows exe icon."""
    # App icon.ico
    icon = app.path / "assets" / "icon.ico"
    if icon.exists():
        print(f"[KislinkaTools] Using app icon: {icon}")
        return icon.resolve()

    # App icon.png -> convert to ICO
    png = app.path / "assets" / "icon.png"
    if png.exists():
        cached = _get_cached_ico_for_png(png)
        if cached:
            print(f"[KislinkaTools] Using converted app icon: {cached}")
            return cached

    # Core default_app.ico
    core_ico = assets_dir() / "another" / "default_app.ico"
    if core_ico.exists():
        print(f"[KislinkaTools] Using core icon: {core_ico}")
        return core_ico.resolve()

    # Core default_app.png -> convert to ICO
    core_png = assets_dir() / "another" / "default_app.png"
    if core_png.exists():
        cached = _get_cached_ico_for_png(core_png)
        if cached:
            print(f"[KislinkaTools] Using converted core icon: {cached}")
            return cached

    print("[KislinkaTools] No icon found for build")
    return None


def build_full(i18n: I18n, app: AppInfo, *, extra_hidden_imports: list[str] | None = None) -> None:
    out_name = f"{app.name}"
    entry = root_dir() / "main.py"

    add_data: list[tuple[Path, str]] = []

    for folder_name in ("core", "widgets", "audio", "graphics"):
        folder = root_dir() / folder_name
        if folder.exists():
            add_data.append((folder, folder.name))

    if assets_dir().exists():
        add_data.append((assets_dir(), "assets"))

    if components_dir().exists():
        add_data.append((components_dir(), "components"))

    # Only selected app, not all apps
    cash = cash_dir()
    cash.mkdir(parents=True, exist_ok=True)
    tmp_root = cash / "tmp_build_full"

    try:
        if app.path.exists():
            tmp_app_root = tmp_root / "App"
            if tmp_app_root.exists():
                shutil.rmtree(tmp_app_root, ignore_errors=True)
            tmp_app_root.mkdir(parents=True, exist_ok=True)
            shutil.copytree(app.path, tmp_app_root / app.path.name, dirs_exist_ok=True)
            add_data.append((tmp_app_root, "App"))

        icon = _resolve_app_icon_for_build(app)

        hidden_imports: list[str] = list(_CORE_HIDDEN_IMPORTS)
        cdir = components_dir()
        if cdir.exists():
            for folder in sorted(cdir.iterdir()):
                if not folder.is_dir() or folder.name.startswith((".", "_")):
                    continue
                hidden_imports += _collect_hidden_imports_from_component_folder(folder)

        if extra_hidden_imports:
            hidden_imports += [m for m in extra_hidden_imports if m]

        if hidden_imports:
            _validate_hidden_imports(hidden_imports)

        _run_pyinstaller(
            i18n,
            name=out_name,
            entry_script=entry,
            add_data=add_data,
            icon_path=icon,
            hidden_imports=sorted(set(hidden_imports)) or None,
        )
    finally:
        if tmp_root.exists():
            shutil.rmtree(tmp_root, ignore_errors=True)


def build_slim(i18n: I18n, app: AppInfo, *, extra_hidden_imports: list[str] | None = None) -> None:
    out_name = f"{app.name}"
    entry = root_dir() / "main.py"

    used = resolve_component_deps(detect_used_components(app.path))

    add_data: list[tuple[Path, str]] = []

    for folder_name in ("core", "widgets", "audio", "graphics"):
        folder = root_dir() / folder_name
        if folder.exists():
            add_data.append((folder, folder.name))

    if assets_dir().exists():
        add_data.append((assets_dir(), "assets"))

    cash = cash_dir()
    cash.mkdir(parents=True, exist_ok=True)
    tmp_root = cash / "tmp_build"

    try:
        # Selected app only.
        if app.path.exists():
            tmp_app_root = tmp_root / "App"
            if tmp_app_root.exists():
                shutil.rmtree(tmp_app_root, ignore_errors=True)
            tmp_app_root.mkdir(parents=True, exist_ok=True)
            shutil.copytree(app.path, tmp_app_root / app.path.name, dirs_exist_ok=True)
            add_data.append((tmp_app_root, "App"))

        # Bundle only the used components, but copy each component folder in full
        # (with all subfolders/files) for maximum compatibility.
        cdir = components_dir()
        if cdir.exists() and used:
            tmp_comp_root = tmp_root / "components"
            if tmp_comp_root.exists():
                shutil.rmtree(tmp_comp_root, ignore_errors=True)
            tmp_comp_root.mkdir(parents=True, exist_ok=True)

            for comp_name in sorted(used):
                src = _get_component_folder_by_name(comp_name)
                if src is not None:
                    shutil.copytree(src, tmp_comp_root / src.name, dirs_exist_ok=True)

            add_data.append((tmp_comp_root, "components"))

        icon = _resolve_app_icon_for_build(app)

        hidden_imports: list[str] = list(_CORE_HIDDEN_IMPORTS)
        for comp_name in sorted(used):
            folder = _get_component_folder_by_name(comp_name)
            if folder is None:
                continue
            hidden_imports += _collect_hidden_imports_from_component_folder(folder)

        if extra_hidden_imports:
            hidden_imports += [m for m in extra_hidden_imports if m]

        if hidden_imports:
            _validate_hidden_imports(hidden_imports)

        _run_pyinstaller(
            i18n,
            name=out_name,
            entry_script=entry,
            add_data=add_data,
            icon_path=icon,
            hidden_imports=sorted(set(hidden_imports)) or None,
        )
    finally:
        if tmp_root.exists():
            shutil.rmtree(tmp_root, ignore_errors=True)
