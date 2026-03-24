from __future__ import annotations

from Components.appscan import list_apps
from Components.build import build_full, build_slim
from Components.cli_utils import input_choice, clear_screen
from Components.demo_app import create_demo_app
from Components.deps import ensure_dependencies
from Components.i18n import I18n


def choose_language() -> str:
    print("Select language / Выберите язык")
    print("  1. English")
    print("  2. Русский")
    val = input_choice("> ", ["1", "2"])
    return "en" if val == "1" else "ru"


def choose_app(i18n: I18n):
    apps = list_apps()
    if not apps:
        print(i18n.t("no_apps_found"))
        raise SystemExit(1)

    print(i18n.t("choose_app"))
    for idx, app in enumerate(apps, start=1):
        print(f"  {idx}. {app.display_name} ({app.path.name})")

    while True:
        raw = input(i18n.t("enter_number")).strip()
        if raw.isdigit():
            i = int(raw)
            if 1 <= i <= len(apps):
                return apps[i - 1]


def input_extra_hidden_imports(i18n: I18n) -> list[str]:
    print()
    print(i18n.t("extra_deps_title"))
    print(i18n.t("extra_deps_line1"))
    print(i18n.t("extra_deps_line2"))
    print(i18n.t("extra_deps_done"))

    mods: list[str] = []
    while True:
        raw = input("> ").strip()
        if not raw:
            break
        mods.append(raw)

    # De-dup but keep order
    uniq: list[str] = []
    seen = set()
    for m in mods:
        if m not in seen:
            uniq.append(m)
            seen.add(m)
    return uniq


def main() -> None:
    lang = choose_language()
    i18n = I18n(lang)

    # Ensure any buffered output is written before clearing.
    try:
        import sys
        sys.stdout.flush()
    except Exception:
        pass
    clear_screen()

    ensure_dependencies(i18n)

    while True:
        print(i18n.t("menu_title"))
        print("  1.", i18n.t("menu_build"))
        print("  2.", i18n.t("menu_create_demo"))
        print("  0.", i18n.t("exit"))

        choice = input_choice(i18n.t("choose_option"), ["1", "2", "0"])
        if choice == "0":
            return

        if choice == "2":
            create_demo_app(i18n)
            print()
            continue

        app = choose_app(i18n)
        extra = input_extra_hidden_imports(i18n)

        print(i18n.t("build_mode"))
        print("  1.", i18n.t("build_full"))
        print("  2.", i18n.t("build_slim"))

        mode = input_choice(i18n.t("choose_option"), ["1", "2"])

        try:
            if mode == "1":
                build_full(i18n, app, extra_hidden_imports=extra)
            else:
                build_slim(i18n, app, extra_hidden_imports=extra)
            print(i18n.t("done"))
        except Exception as exc:
            print(i18n.t("build_error"), str(exc))

        print()


if __name__ == "__main__":
    main()
