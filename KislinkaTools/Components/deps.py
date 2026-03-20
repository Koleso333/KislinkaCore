from __future__ import annotations

import subprocess
import sys

from Components.cli_utils import yes_no
from Components.cli_utils import run_silent_with_spinner
from Components.i18n import I18n


def _module_available(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False


def ensure_dependencies(i18n: I18n) -> None:
    missing = []
    if not _module_available("PyInstaller"):
        missing.append("pyinstaller")
    if not _module_available("PIL"):
        missing.append("pillow")

    if not missing:
        return

    print(f"Missing dependencies: {', '.join(missing)}")
    if not yes_no("Install now?", default_yes=True):
        print("Installation cancelled.")
        raise SystemExit(1)

    cmd = [sys.executable, "-m", "pip", "install"] + missing
    try:
        run_silent_with_spinner(cmd)
    except subprocess.CalledProcessError as exc:
        print(i18n.t("install_failed"), str(exc))
        raise SystemExit(1)
