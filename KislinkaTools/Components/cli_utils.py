from __future__ import annotations

import subprocess
import sys
import threading
import time
import os
from collections.abc import Sequence

def input_choice(prompt: str, choices: list[str]) -> str:
    choices_lower = {c.lower(): c for c in choices}
    while True:
        val = input(prompt).strip().lower()
        if val in choices_lower:
            return choices_lower[val]

def yes_no(prompt: str, default_yes: bool = True) -> bool:
    suffix = "[Y/n]" if default_yes else "[y/N]"
    while True:
        val = input(f"{prompt} {suffix} ").strip().lower()
        if not val:
            return default_yes
        if val in ("y", "yes"):
            return True
        if val in ("n", "no"):
            return False

def clear_screen() -> None:
    # Best-effort clear that works even after '\r' spinner output.
    try:
        sys.stdout.write("\r" + (" " * 250) + "\r")
        sys.stdout.flush()
    except Exception:
        pass

    # ANSI clear + cursor home (works in many modern terminals, incl. Windows Terminal).
    try:
        sys.stdout.write("\x1b[2J\x1b[H")
        sys.stdout.flush()
        return
    except Exception:
        pass

    # Fallback.
    os.system("cls" if os.name == "nt" else "clear")

def run_silent_with_spinner(
    cmd: Sequence[str],
    *,
    cwd: str | None = None,
    show_last_line: bool = False,
) -> None:
    frames = ["/", "-", "\\", "|"]
    stop = threading.Event()
    last_line_lock = threading.Lock()
    last_line: str = ""

    def _set_last_line(val: str) -> None:
        nonlocal last_line
        cleaned = val.replace("\r", " ").replace("\n", " ").strip()
        if not cleaned:
            return
        with last_line_lock:
            last_line = cleaned

    def _get_last_line() -> str:
        with last_line_lock:
            return last_line

    def spinner() -> None:
        i = 0
        while not stop.is_set():
            frame = frames[i % len(frames)]
            i += 1
            if show_last_line:
                line = _get_last_line()
                # Keep it one-line and reasonably short.
                if len(line) > 140:
                    line = line[:137] + "..."
                sys.stdout.write("\r" + frame + " " + line)
            else:
                sys.stdout.write("\r" + frame)
            sys.stdout.flush()
            time.sleep(0.05)
        # Clear current line.
        sys.stdout.write("\r" + (" " * 200) + "\r")
        sys.stdout.flush()

    t = threading.Thread(target=spinner, daemon=True)
    t.start()
    try:
        if not show_last_line:
            proc = subprocess.run(
                list(cmd),
                cwd=cwd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            rc = proc.returncode
        else:
            p = subprocess.Popen(
                list(cmd),
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )
            assert p.stdout is not None
            for line in p.stdout:
                _set_last_line(line)
            rc = p.wait()
    finally:
        stop.set()
        t.join(timeout=1)

    if rc != 0:
        raise subprocess.CalledProcessError(rc, list(cmd))
