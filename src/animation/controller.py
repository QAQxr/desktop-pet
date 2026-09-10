from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QElapsedTimer, QObject, Qt, QTimer, Signal

from .clock import AnimationClock
from .transform import AnimationTransform


class AnimationController(QObject):
    """Drives the current animation with a Qt timer and emits transforms.

    The controller never touches the window's real position; it only emits
    visual offsets. The window decides how to render them.
    """

    frame_changed = Signal(object)

    def __init__(self, animation, fps: int = 30, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._animation = animation
        self._clock = AnimationClock()
        self._elapsed = QElapsedTimer()
        self._current = AnimationTransform.identity()
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.PreciseTimer)
        self._timer.setInterval(max(1, int(round(1000.0 / max(1, fps)))))
        self._timer.timeout.connect(self._on_tick)

    @property
    def fps(self) -> float:
        return 1000.0 / self._timer.interval()

    @property
    def animation(self):
        return self._animation

    @property
    def is_running(self) -> bool:
        return self._clock.running and not self._clock.paused

    @property
    def is_paused(self) -> bool:
        return self._clock.paused

    def current(self) -> AnimationTransform:
        return self._current

    def start(self) -> None:
        self._elapsed.start()
        self._clock.start(self._now())
        self._current = self._animation.sample(0.0)
        self._timer.start()
        self._emit()

    def pause(self) -> None:
        self._clock.pause(self._now())
        self._timer.stop()

    def resume(self) -> None:
        self._clock.resume(self._now())
        if self._clock.running and not self._clock.paused:
            self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self._clock.stop()
        self._current = AnimationTransform.identity()
        self._emit()

    def _on_tick(self) -> None:
        self._current = self._animation.sample(self._clock.time(self._now()))
        self._emit()

    def _emit(self) -> None:
        self.frame_changed.emit(self._current)

    def _now(self) -> float:
        if not self._elapsed.isValid():
            self._elapsed.start()
        return self._elapsed.elapsed() / 1000.0
