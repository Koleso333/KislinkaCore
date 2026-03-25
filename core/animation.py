"""Centralized animation system.

KAnimator provides a unified API for all animations in KislinkaCore.

Usage from widgets::

    from core.animation import KAnimator, KEasing

    # Simple property animation
    anim = KAnimator.animate(
        widget, b"pos",
        start=QPoint(0, 0), end=QPoint(100, 0),
        duration=250, easing=KEasing.OUT_CUBIC,
    )

    # Float tween (no target object)
    anim = KAnimator.tween(
        start=0.0, end=1.0,
        duration=300, easing=KEasing.OUT_CUBIC,
        on_value=lambda v: widget.setOpacity(v),
        on_done=lambda: widget.hide(),
    )

    # Group — parallel
    group = KAnimator.parallel(anim_a, anim_b, on_done=callback)

    # Get frame interval (ms) matched to monitor refresh
    interval = KAnimator.frame_interval()   # e.g. 7 for 144 Hz
"""

from __future__ import annotations

from typing import Any, Callable

from PyQt6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QObject,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QSequentialAnimationGroup,
    QVariantAnimation,
)
from PyQt6.QtWidgets import QApplication


# ── Easing presets ──────────────────────────────────────────────


class KEasing:
    """Shorthand easing constants."""

    LINEAR      = QEasingCurve.Type.Linear
    IN_QUAD     = QEasingCurve.Type.InQuad
    OUT_QUAD    = QEasingCurve.Type.OutQuad
    IN_OUT_QUAD = QEasingCurve.Type.InOutQuad
    IN_CUBIC    = QEasingCurve.Type.InCubic
    OUT_CUBIC   = QEasingCurve.Type.OutCubic
    IN_OUT_CUBIC = QEasingCurve.Type.InOutCubic
    IN_QUART    = QEasingCurve.Type.InQuart
    OUT_QUART   = QEasingCurve.Type.OutQuart
    IN_OUT_QUART = QEasingCurve.Type.InOutQuart
    IN_EXPO     = QEasingCurve.Type.InExpo
    OUT_EXPO    = QEasingCurve.Type.OutExpo
    IN_OUT_EXPO = QEasingCurve.Type.InOutExpo
    IN_BACK     = QEasingCurve.Type.InBack
    OUT_BACK    = QEasingCurve.Type.OutBack
    IN_OUT_BACK = QEasingCurve.Type.InOutBack
    IN_ELASTIC  = QEasingCurve.Type.InElastic
    OUT_ELASTIC = QEasingCurve.Type.OutElastic


# ── Tween (value-only animation) ───────────────────────────────


class _Tween(QVariantAnimation):
    """Float tween that calls *on_value* each frame."""

    def __init__(
        self,
        start: float,
        end: float,
        duration: int,
        easing: QEasingCurve.Type,
        on_value: Callable[[float], Any] | None,
        on_done: Callable[[], Any] | None,
        parent: QObject | None,
    ) -> None:
        super().__init__(parent)
        self.setStartValue(float(start))
        self.setEndValue(float(end))
        self.setDuration(duration)
        self.setEasingCurve(easing)
        self._on_value = on_value
        if on_done:
            self.finished.connect(on_done)

    def updateCurrentValue(self, value: Any) -> None:  # noqa: N802
        if self._on_value:
            self._on_value(float(value))


# ── KAnimator ──────────────────────────────────────────────────


class KAnimator:
    """Static helper — centralised animation factory."""

    # Cached per-run so we don't query the screen every call.
    _cached_interval: int | None = None

    # ── monitor-synced frame interval ──────────────────────────

    @staticmethod
    def frame_interval() -> int:
        """Milliseconds per frame for the primary screen.

        Falls back to 16 ms (~60 Hz) if the refresh rate is unknown.
        """
        if KAnimator._cached_interval is not None:
            return KAnimator._cached_interval

        interval = 16  # default 60 Hz
        app = QApplication.instance()
        if app is not None:
            screen = QApplication.primaryScreen()
            if screen is not None:
                hz = screen.refreshRate()
                if hz and hz > 0:
                    interval = max(1, int(1000.0 / hz))

        KAnimator._cached_interval = interval
        return interval

    @staticmethod
    def refresh_rate() -> float:
        """Primary screen refresh rate in Hz (0 if unknown)."""
        app = QApplication.instance()
        if app is not None:
            screen = QApplication.primaryScreen()
            if screen is not None:
                return screen.refreshRate()
        return 0.0

    @staticmethod
    def reset_cache() -> None:
        """Force re-detection on next call (e.g. after monitor change)."""
        KAnimator._cached_interval = None

    # ── property animation ─────────────────────────────────────

    @staticmethod
    def animate(
        target: QObject,
        prop: bytes,
        *,
        start: Any,
        end: Any,
        duration: int = 250,
        easing: QEasingCurve.Type = KEasing.OUT_CUBIC,
        on_done: Callable[[], Any] | None = None,
        parent: QObject | None = None,
        loops: int = 1,
    ) -> QPropertyAnimation:
        """Create and return a ``QPropertyAnimation``.

        The animation is **not started** — call ``.start()`` yourself
        so you can connect extra signals first if needed.
        """
        anim = QPropertyAnimation(target, prop, parent or target)
        anim.setDuration(duration)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(easing)
        anim.setLoopCount(loops)

        if on_done:
            anim.finished.connect(on_done)

        return anim

    @staticmethod
    def start(
        target: QObject,
        prop: bytes,
        *,
        start: Any,
        end: Any,
        duration: int = 250,
        easing: QEasingCurve.Type = KEasing.OUT_CUBIC,
        on_done: Callable[[], Any] | None = None,
        parent: QObject | None = None,
    ) -> QPropertyAnimation:
        """Create, start, and return the animation in one call."""
        anim = KAnimator.animate(
            target, prop,
            start=start, end=end,
            duration=duration, easing=easing,
            on_done=on_done, parent=parent,
        )
        anim.start()
        return anim

    # ── value tween (no target) ────────────────────────────────

    @staticmethod
    def tween(
        *,
        start: float = 0.0,
        end: float = 1.0,
        duration: int = 300,
        easing: QEasingCurve.Type = KEasing.OUT_CUBIC,
        on_value: Callable[[float], Any] | None = None,
        on_done: Callable[[], Any] | None = None,
        parent: QObject | None = None,
    ) -> _Tween:
        """Float-only animation with per-frame callback."""
        t = _Tween(start, end, duration, easing, on_value, on_done, parent)
        return t

    # ── groups ─────────────────────────────────────────────────

    @staticmethod
    def parallel(
        *anims: QAbstractAnimation,
        on_done: Callable[[], Any] | None = None,
        parent: QObject | None = None,
    ) -> QParallelAnimationGroup:
        """Run several animations simultaneously."""
        group = QParallelAnimationGroup(parent)
        for a in anims:
            group.addAnimation(a)
        if on_done:
            group.finished.connect(on_done)
        return group

    @staticmethod
    def sequence(
        *anims: QAbstractAnimation,
        on_done: Callable[[], Any] | None = None,
        parent: QObject | None = None,
    ) -> QSequentialAnimationGroup:
        """Run animations one after another."""
        group = QSequentialAnimationGroup(parent)
        for a in anims:
            group.addAnimation(a)
        if on_done:
            group.finished.connect(on_done)
        return group
