"""
Hook system for KislinkaCore components.

Two types of hooks:
    emit   — fire-and-forget notification (no return value)
    filter — value passes through a chain of handlers, each can modify it

Usage:
    hooks = HookManager.instance()

    # register a handler
    hooks.register("after_theme_change", my_callback, priority=10)

    # emit (notify all listeners)
    hooks.emit("after_theme_change", theme_name="dark")

    # filter (pass value through chain)
    qss = hooks.filter("core_qss", qss_string, theme=theme_obj)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


def _log(msg: str) -> None:
    print(f"[Hooks] {msg}")


@dataclass
class _HookEntry:
    callback: Callable
    priority: int
    owner: str  # component name or "core"


class HookManager:
    """Singleton hook registry."""

    _instance: HookManager | None = None

    def __init__(self) -> None:
        if HookManager._instance is not None:
            raise RuntimeError("Use HookManager.instance()")
        HookManager._instance = self
        self._hooks: dict[str, list[_HookEntry]] = {}

    @classmethod
    def instance(cls) -> HookManager:
        if cls._instance is None:
            cls()
        return cls._instance

    # ── register / unregister ───────────────────────

    def register(
        self,
        event: str,
        callback: Callable,
        *,
        priority: int = 100,
        owner: str = "core",
    ) -> None:
        """
        Register a handler for an event.

        priority: lower number = called first (default 100)
        owner:    component name (used for bulk unregister)
        """
        entry = _HookEntry(callback=callback, priority=priority, owner=owner)

        if event not in self._hooks:
            self._hooks[event] = []

        self._hooks[event].append(entry)
        self._hooks[event].sort(key=lambda e: e.priority)

    def unregister(self, event: str, callback: Callable) -> bool:
        """Remove a specific callback from an event."""
        entries = self._hooks.get(event)
        if not entries:
            return False

        before = len(entries)
        self._hooks[event] = [e for e in entries if e.callback is not callback]
        return len(self._hooks[event]) < before

    def unregister_owner(self, owner: str) -> int:
        """Remove ALL hooks registered by a given owner. Returns count removed."""
        removed = 0
        for event in list(self._hooks):
            before = len(self._hooks[event])
            self._hooks[event] = [
                e for e in self._hooks[event] if e.owner != owner
            ]
            removed += before - len(self._hooks[event])

            if not self._hooks[event]:
                del self._hooks[event]

        if removed:
            _log(f"Unregistered {removed} hook(s) from '{owner}'")
        return removed

    def clear(self) -> None:
        """Remove all hooks."""
        self._hooks.clear()

    # ── emit (fire-and-forget) ──────────────────────

    def emit(self, event: str, **kwargs: Any) -> None:
        """
        Call all handlers for event. No return value.

        Example:
            hooks.emit("after_theme_change", theme_name="dark")
        """
        entries = self._hooks.get(event)
        if not entries:
            return

        for entry in entries:
            try:
                entry.callback(**kwargs)
            except Exception as exc:
                _log(f"⚠ Hook error [{event}] owner={entry.owner}: {exc}")

    # ── filter (value passes through chain) ─────────

    def filter(self, event: str, value: Any, **kwargs: Any) -> Any:
        """
        Pass value through all handlers. Each handler receives (value, **kwargs)
        and returns modified (or same) value.

        Example:
            qss = hooks.filter("core_qss", qss_string, theme=t)
        """
        entries = self._hooks.get(event)
        if not entries:
            return value

        for entry in entries:
            try:
                result = entry.callback(value, **kwargs)
                if result is not None:
                    value = result
            except Exception as exc:
                _log(f"⚠ Filter error [{event}] owner={entry.owner}: {exc}")

        return value

    # ── introspection ───────────────────────────────

    def list_events(self) -> list[str]:
        """List all registered event names."""
        return sorted(self._hooks.keys())

    def list_handlers(self, event: str) -> list[dict]:
        """List handlers for an event."""
        entries = self._hooks.get(event, [])
        return [
            {"owner": e.owner, "priority": e.priority, "callback": e.callback.__name__}
            for e in entries
        ]

    def has_handlers(self, event: str) -> bool:
        """Check if event has any handlers."""
        return bool(self._hooks.get(event))
