"""
Localization system.

Core and App have INDEPENDENT languages.
If a language exists in both — both switch.
If only in one — only that one switches.
"""

import json
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal


CORE_LOCALES_DIR = Path(__file__).resolve().parent / "locales"

_LANG_NAMES = {
    "en": "English",
    "ru": "Русский",
    "es": "Español",
    "de": "Deutsch",
    "fr": "Français",
    "ja": "日本語",
    "zh": "中文",
    "ko": "한국어",
    "pt": "Português",
    "it": "Italiano",
}


def _log(msg: str):
    print(f"[Locale] {msg}")


class LocaleManager(QObject):
    """Singleton locale manager with independent core/app languages."""

    changed = pyqtSignal()

    _instance: "LocaleManager | None" = None

    def __init__(self):
        if LocaleManager._instance is not None:
            raise RuntimeError("Use LocaleManager.instance()")
        super().__init__()
        LocaleManager._instance = self

        self._core_language = "en"
        self._app_language = "en"
        self._core_strings: dict[str, dict] = {}
        self._app_strings: dict[str, dict] = {}
        self._has_app = False

        self._load_core_locales()

    @classmethod
    def instance(cls) -> "LocaleManager":
        if cls._instance is None:
            cls()
        return cls._instance

    # ── language ────────────────────────────────────

    @property
    def language(self) -> str:
        """Returns core language (used for display in settings)."""
        return self._core_language

    @property
    def core_language(self) -> str:
        return self._core_language

    @property
    def app_language(self) -> str:
        return self._app_language

    def set_language(self, lang: str):
        """
        Set language. Independently applies to core and app.
        - If lang exists in core → core switches
        - If lang exists in app → app switches
        - If lang missing in one → that one keeps its previous language
        """
        changed = False

        if lang in self._core_strings:
            if self._core_language != lang:
                self._core_language = lang
                _log(f"Core language set: {lang}")
                changed = True
        else:
            _log(f"Language '{lang}' not in core, core stays on '{self._core_language}'")

        if self._has_app:
            if lang in self._app_strings:
                if self._app_language != lang:
                    self._app_language = lang
                    _log(f"App language set: {lang}")
                    changed = True
            else:
                _log(f"Language '{lang}' not in app, app stays on '{self._app_language}'")
        else:
            # no app — app language follows core
            self._app_language = self._core_language

        if changed:
            self.changed.emit()

    def validate_language(self):
        """
        After loading app locales, make sure app_language is valid.
        If current app_language doesn't exist in app, find best fallback.
        """
        if not self._has_app:
            return

        if self._app_language not in self._app_strings:
            fallback = self._find_app_fallback()
            if fallback:
                _log(f"App language '{self._app_language}' not available, falling back to '{fallback}'")
                self._app_language = fallback

    # ── translate ───────────────────────────────────

    def t(self, key: str, fallback: str = "") -> str:
        """
        Get translated string.
        Core keys use core_language, app keys use app_language.
        Priority: app strings (app_lang) → core strings (core_lang) → english → key
        """
        # try app strings with app language
        app_lang_strings = self._app_strings.get(self._app_language, {})
        if key in app_lang_strings:
            return app_lang_strings[key]

        # try core strings with core language
        core_lang_strings = self._core_strings.get(self._core_language, {})
        if key in core_lang_strings:
            return core_lang_strings[key]

        # fallback to english in app
        app_en = self._app_strings.get("en", {})
        if key in app_en:
            return app_en[key]

        # fallback to english in core
        core_en = self._core_strings.get("en", {})
        if key in core_en:
            return core_en[key]

        return fallback or key

    # ── available languages ─────────────────────────

    def available_languages(self) -> list[dict]:
        """
        Returns list of all known languages.

        Each entry: {
            "code": "en",
            "name": "English",
            "in_core": True,
            "in_app": True,
            "availability": "both" | "only_in_core" | "only_in_app",
        }
        """
        core_langs = set(self._core_strings.keys())
        app_langs = set(self._app_strings.keys()) if self._has_app else set()
        all_langs = core_langs | app_langs

        result = []
        for code in sorted(all_langs):
            in_core = code in core_langs
            in_app = code in app_langs

            if in_core and in_app:
                avail = "both"
            elif in_core:
                avail = "only_in_core"
            else:
                avail = "only_in_app"

            name = _LANG_NAMES.get(code, code.upper())

            result.append({
                "code": code,
                "name": name,
                "in_core": in_core,
                "in_app": in_app,
                "availability": avail,
            })

        return result

    # ── app locales ─────────────────────────────────

    def load_app_locales(self, app_dir: Path):
        """Load app locale files from app_dir/locales/"""
        self._app_strings.clear()
        self._has_app = True
        locales_dir = app_dir / "locales"

        if not locales_dir.exists():
            _log(f"No app locales dir: {locales_dir}")
            self.validate_language()
            return

        for fp in sorted(locales_dir.iterdir()):
            if fp.suffix.lower() == ".json":
                lang = fp.stem.lower()
                data = self._load_json(fp)
                if data:
                    self._app_strings[lang] = data
                    _log(f"App locale loaded: {lang} ({len(data)} strings)")

        self.validate_language()

    def clear_app_locales(self):
        self._app_strings.clear()
        self._has_app = False

    # ── private ─────────────────────────────────────

    def _find_app_fallback(self) -> str | None:
        """Find best fallback language for app."""
        app_langs = set(self._app_strings.keys())
        if not app_langs:
            return self._core_language

        # prefer core_language if available in app
        if self._core_language in app_langs:
            return self._core_language

        # prefer en, ru
        for pref in ["en", "ru"]:
            if pref in app_langs:
                return pref

        return sorted(app_langs)[0]

    def _load_core_locales(self):
        if not CORE_LOCALES_DIR.exists():
            _log(f"⚠ Core locales dir missing: {CORE_LOCALES_DIR}")
            return

        for fp in sorted(CORE_LOCALES_DIR.iterdir()):
            if fp.suffix.lower() == ".json":
                lang = fp.stem.lower()
                data = self._load_json(fp)
                if data:
                    self._core_strings[lang] = data
                    _log(f"Core locale loaded: {lang} ({len(data)} strings)")

    def _load_json(self, path: Path) -> dict:
        try:
            text = path.read_text(encoding="utf-8")
            data = json.loads(text)
            return data if isinstance(data, dict) else {}
        except Exception as e:
            _log(f"⚠ Locale load error {path.name}: {e}")
            return {}