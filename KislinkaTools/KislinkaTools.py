"""KislinkaTools launcher.

Keep this file minimal.
All tool logic lives in KislinkaTools/Components.
"""
import sys
from pathlib import Path


def main() -> None:
    tools_dir = Path(__file__).resolve().parent
    components_dir = tools_dir / "Components"
    sys.path.insert(0, str(components_dir))

    from cli import main as cli_main

    cli_main()


if __name__ == "__main__":
    main()
