from __future__ import annotations

from typing import Optional


class AnimationClock:
    """Pause-aware monotonic clock, independent of Qt.

    All times are seconds supplied by the caller, which keeps the pause /
    resume semantics unit-testable without an event loop.
    """

    def __init__(self) -> None:
        self._running = False
        self._paused = False
        self._start = 0.0
        self._pause_started: Optional[float] = None
        self._paused_total = 0.0

    @property
    def running(self) -> bool:
        return self._running

    @property
    def paused(self) -> bool:
        return self._running and self._paused

    def start(self, now: float) -> float:
        self._running = True
        self._paused = False
        self._start = now
        self._pause_started = None
        self._paused_total = 0.0
        return self.time(now)

    def pause(self, now: float) -> float:
        if self._running and not self._paused:
            self._paused = True
            self._pause_started = now
        return self.time(now)

    def resume(self, now: float) -> float:
        if self._running and self._paused:
            if self._pause_started is not None:
                self._paused_total += now - self._pause_started
            self._paused = False
            self._pause_started = None
        return self.time(now)

    def stop(self) -> None:
        self._running = False
        self._paused = False
        self._pause_started = None

    def time(self, now: float) -> float:
        if not self._running:
            return 0.0
        reference = self._pause_started if self._paused else now
        return max(reference - self._start - self._paused_total, 0.0)
