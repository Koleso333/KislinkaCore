"""
Scene system with slide transitions.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve,
    QPoint, pyqtSignal,
)


class Scene(QWidget):
    """Base scene."""

    def __init__(self, name: str = "", parent=None):
        super().__init__(parent)
        self._name = name

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self.setObjectName(f"Scene_{name}")

    @property
    def name(self) -> str:
        return self._name

    def scene_layout(self) -> QVBoxLayout:
        return self._layout

    def on_enter(self):
        pass

    def on_leave(self):
        pass


class AnimationType:
    NONE        = "none"
    FADE        = "slide_left"   # alias to slide for compatibility
    SLIDE_LEFT  = "slide_left"
    SLIDE_RIGHT = "slide_right"


class SceneManager(QWidget):
    """Manages scene stack with slide transitions."""

    scene_changed = pyqtSignal(str)
    DURATION = 220

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stack: list[Scene] = []
        self._current: Scene | None = None
        self._animating = False
        self._anim_new: QPropertyAnimation | None = None
        self._anim_old: QPropertyAnimation | None = None

    @property
    def current(self) -> Scene | None:
        return self._current

    @property
    def stack_depth(self) -> int:
        return len(self._stack)

    @property
    def is_animating(self) -> bool:
        return self._animating

    def push(self, scene: Scene, animation: str = AnimationType.SLIDE_LEFT):
        if self._animating:
            return
        old = self._current
        self._stack.append(scene)
        self._current = scene
        self._transition(old, scene, animation)

    def pop(self, animation: str = AnimationType.SLIDE_RIGHT) -> Scene | None:
        if self._animating or len(self._stack) <= 1:
            return None
        old = self._stack.pop()
        self._current = self._stack[-1]
        self._transition(old, self._current, animation, removing=old)
        return old

    def replace(self, scene: Scene, animation: str = AnimationType.SLIDE_LEFT):
        if self._animating:
            return
        old = self._current
        removing = self._stack.pop() if self._stack else None
        self._stack.append(scene)
        self._current = scene
        self._transition(old, scene, animation, removing=removing)

    def _transition(self, old: Scene | None, new: Scene, animation: str, removing: Scene | None = None):
        new.setParent(self)
        new.resize(self.size())

        # no animation
        if animation == AnimationType.NONE or old is None:
            new.move(0, 0)
            new.show()
            new.raise_()
            new.on_enter()
            if old and old is not new:
                old.on_leave()
                old.hide()
            if removing and removing is not new:
                removing.hide()
                removing.setParent(None)
            self.scene_changed.emit(new.name)
            return

        # slide animation
        self._animating = True
        w = self.width()

        if animation == AnimationType.SLIDE_LEFT:
            new_start = w
            old_end = -w
        else:  # SLIDE_RIGHT
            new_start = -w
            old_end = w

        new.move(new_start, 0)
        new.show()
        new.raise_()

        # animate new scene
        self._anim_new = QPropertyAnimation(new, b"pos", self)
        self._anim_new.setDuration(self.DURATION)
        self._anim_new.setStartValue(QPoint(new_start, 0))
        self._anim_new.setEndValue(QPoint(0, 0))
        self._anim_new.setEasingCurve(QEasingCurve.Type.OutCubic)

        # animate old scene
        self._anim_old = QPropertyAnimation(old, b"pos", self)
        self._anim_old.setDuration(self.DURATION)
        self._anim_old.setStartValue(QPoint(0, 0))
        self._anim_old.setEndValue(QPoint(old_end, 0))
        self._anim_old.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._finish_count = 0
        self._old_scene = old
        self._new_scene = new
        self._removing = removing

        self._anim_new.finished.connect(self._on_anim_finished)
        self._anim_old.finished.connect(self._on_anim_finished)

        self._anim_new.start()
        self._anim_old.start()

    def _on_anim_finished(self):
        self._finish_count += 1
        if self._finish_count < 2:
            return

        self._animating = False
        self._new_scene.on_enter()

        if self._old_scene and self._old_scene is not self._new_scene:
            self._old_scene.on_leave()
            self._old_scene.hide()
            self._old_scene.move(0, 0)

        if self._removing and self._removing is not self._new_scene:
            self._removing.hide()
            self._removing.setParent(None)

        self.scene_changed.emit(self._new_scene.name)

        self._anim_new = None
        self._anim_old = None
        self._old_scene = None
        self._new_scene = None
        self._removing = None

    def _force_pop(self):
        """Pop instantly without animation. Used internally by settings."""
        if len(self._stack) <= 1:
            return
        old = self._stack.pop()
        self._current = self._stack[-1]

        self._current.setParent(self)
        self._current.resize(self.size())
        self._current.move(0, 0)
        self._current.show()
        self._current.raise_()
        self._current.on_enter()

        if old is not self._current:
            old.on_leave()
            old.hide()
            old.setParent(None)

        self.scene_changed.emit(self._current.name)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._current and not self._animating:
            self._current.resize(self.size())
            self._current.move(0, 0)