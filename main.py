"""KislinkaCore entry point."""

from core.app import KislinkaApp


def main():
    app = KislinkaApp()
    app.run()


if __name__ == "__main__":
    main()