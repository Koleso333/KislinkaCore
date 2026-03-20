"""KislinkaTools launcher.

Keep this file minimal.
All tool logic lives in KislinkaTools/Components.
"""
import sys
import json
from pathlib import Path


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _collect_issues(root_dir: Path, tools_dir: Path) -> list[str]:
    issues: list[str] = []

    components_dir = tools_dir / "Components"
    if not components_dir.exists():
        issues.append(f"Missing directory: {components_dir}")
    else:
        cli_py = components_dir / "cli.py"
        if not cli_py.exists():
            issues.append(f"Missing entry point module: {cli_py}")

    apps_dir = root_dir / "App"
    if not apps_dir.exists():
        issues.append(f"Missing directory: {apps_dir}")
        return issues

    app_folders = [p for p in sorted(apps_dir.iterdir()) if p.is_dir() and not p.name.startswith((".", "_"))]
    if not app_folders:
        issues.append(f"No apps found in: {apps_dir}")
        return issues

    any_valid = False
    for app_dir in app_folders:
        manifest_path = app_dir / "manifest.json"
        if not manifest_path.exists():
            issues.append(f"{app_dir.name}: missing manifest.json")
            continue

        data = _read_json(manifest_path)
        if data is None:
            issues.append(f"{app_dir.name}: manifest.json is invalid JSON")
            continue

        entry_point = str(data.get("entry_point", "main.py"))
        entry_file = app_dir / entry_point
        if not entry_file.exists():
            issues.append(f"{app_dir.name}: entry_point not found: {entry_point}")
            continue

        main_class = str(data.get("main_class", "")).strip()
        if not main_class:
            issues.append(f"{app_dir.name}: main_class is missing in manifest.json")
            continue

        any_valid = True

    if not any_valid:
        issues.append("No valid app manifests found (at least one app must have manifest.json + entry_point + main_class)")

    return issues


def _print_diagnostics(issues: list[str]) -> None:
    print("KislinkaTools started in fallback mode.")
    if not issues:
        print("No critical issues found.")
        return

    print("Problems detected:")
    for item in issues:
        print(f"- {item}")
    print("Fix the items above or restore KislinkaTools/Components/cli.py to enable full functionality.")


def main() -> None:
    tools_dir = Path(__file__).resolve().parent
    components_dir = tools_dir / "Components"
    sys.path.insert(0, str(components_dir))

    try:
        from cli import main as cli_main
    except ModuleNotFoundError:
        root_dir = tools_dir.parent
        issues = _collect_issues(root_dir, tools_dir)
        _print_diagnostics(issues)
        return

    cli_main()


if __name__ == "__main__":
    main()
