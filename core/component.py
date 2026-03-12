"""
Base class for KislinkaCore components.

Subclass KislinkaComponent and override lifecycle methods
to extend or modify core behavior.

Example:

    from core.component import KislinkaComponent

    class Notifier(KislinkaComponent):

        def on_register(self, core):
            self.core = core
            core.hooks.register("after_theme_change", self._on_theme)

        def on_ready(self):
            print("Notifier ready — all components loaded")

        def on_app_setup(self, app_instance):
            print(f"App loaded: {app_instance}")

        def on_unload(self):
            print("Notifier unloaded")

        # ── public API (called by apps) ─────────────
        def show(self, message: str):
            print(f"[Notifier] {message}")

        # ── hook handler ────────────────────────────
        def _on_theme(self, **kwargs):
            print(f"Theme changed to {kwargs.get('theme_name')}")
"""

from __future__ import annotations


class KislinkaComponent:
    """
    Base class for all KislinkaCore components.

    Lifecycle:
        1. on_register(core)   — component loaded, core reference available
        2. on_ready()          — ALL components loaded, safe to reference others
        3. on_app_setup(inst)  — user app's setup() completed
        4. on_app_cleanup()    — before user app's cleanup()
        5. on_unload()         — component being removed, clean up resources

    Components can:
        - Register hooks to intercept/modify core behavior
        - Expose public API for apps via app.components.get("Name")
        - Provide widget classes, utilities, services
    """

    @property
    def name(self) -> str:
        """Component name (defaults to class name)."""
        return self.__class__.__name__

    # ── lifecycle ───────────────────────────────────

    def on_register(self, core) -> None:
        """
        Called when the component is loaded and registered.

        core: KislinkaApp instance — full access to all managers:
            core.hooks            — HookManager
            core.theme_manager    — ThemeManager
            core.storage          — StorageManager
            core.locale           — LocaleManager
            core.audio            — AudioPlayer
            core.permissions      — PermissionManager
            core.components       — ComponentManager

        Use this to:
            - Store reference to core
            - Register hooks via core.hooks.register(...)
            - Read config from storage
            - Initialize internal state
        """
        pass

    def on_ready(self) -> None:
        """
        Called after ALL components are loaded and registered.

        Safe to look up and interact with other components here:
            other = core.components.get("OtherComponent")
        """
        pass

    def on_app_setup(self, app_instance) -> None:
        """
        Called after the user application's setup() completes.

        app_instance: the user's main app object.
        """
        pass

    def on_app_cleanup(self) -> None:
        """Called before the user application's cleanup() runs."""
        pass

    def on_unload(self) -> None:
        """
        Called when the component is being unloaded (shutdown / reload).

        Clean up resources, disconnect hooks, stop timers.
        Hook unregistration by owner name is done automatically
        by ComponentManager — you don't need to do it manually.
        """
        pass
