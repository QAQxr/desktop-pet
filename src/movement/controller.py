from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QElapsedTimer, QObject, Qt, QTimer, Signal

from .movement import MovementModel, MovementState


class MovementController(QObject):
    """Drives a ``MovementModel`` with a Qt timer.

    Only computes world positions and emits them; it never renders. Delta time
    comes from ``QElapsedTimer`` so movement speed is frame-rate independent.
    """

    position_changed = Signal(object)
    state_changed = Signal(object)

    def __init__(self, model: MovementModel, fps: int = 60, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._model = model
        self._elapsed = QElapsedTimer()
        self._last = 0.0
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.PreciseTimer)
        self._timer.setInterval(max(1, int(round(1000.0 / max(1, fps)))))
        self._timer.timeout.connect(self._on_tick)

    @property
    def model(self) -> MovementModel:
        return self._model

    @property
    def is_running(self) -> bool:
        return self._timer.isActive()

    @property
    def state(self) -> MovementState:
        return self._model.state

    def start(self) -> None:
        if self._model.state is MovementState.IDLE:
            self._model.start()
        self._elapsed.start()
        self._last = 0.0
        self._timer.start()
        self.position_changed.emit(self._model.position)
        self.state_changed.emit(self._model.state)

    def pause(self) -> None:
        self._timer.stop()
        self._model.pause()
        self.state_changed.emit(self._model.state)

    def resume(self) -> None:
        if self._model.state is MovementState.PAUSED:
            self._model.resume()
            self._elapsed.restart()
            self._last = 0.0
            self._timer.start()
            self.state_changed.emit(self._model.state)

    def stop(self) -> None:
        self._timer.stop()
        self._model.stop()
        self.state_changed.emit(self._model.state)

    def _on_tick(self) -> None:
        now = self._elapsed.elapsed() / 1000.0
        delta_time = now - self._last
        self._last = now
        if self._model.advance(delta_time):
            self.position_changed.emit(self._model.position)
        if self._model.state is not MovementState.WALKING:
            self._timer.stop()
            self.state_changed.emit(self._model.state)
