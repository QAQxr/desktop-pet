from __future__ import annotations

from enum import Enum
from typing import Optional

from .bounds import MovementBounds
from .position import WorldPosition


class Direction(Enum):
    LEFT = (-1.0, 0.0)
    RIGHT = (1.0, 0.0)
    UP = (0.0, -1.0)
    DOWN = (0.0, 1.0)

    @classmethod
    def from_name(cls, name: str) -> "Direction":
        try:
            return cls[name.strip().upper()]
        except KeyError as exc:
            raise ValueError(f"unknown direction: {name!r}") from exc


class MovementState(Enum):
    IDLE = "idle"
    WALKING = "walking"
    PAUSED = "paused"


class MovementModel:
    """Pure time-based movement model.

    ``position += velocity * delta_time`` with clamping to ``MovementBounds``.
    Reaching a boundary clamps the position and stops movement. No Qt, no
    painting, no acceleration/physics.
    """

    def __init__(
        self,
        position: WorldPosition,
        speed: float,
        bounds: MovementBounds,
        direction: Direction = Direction.RIGHT,
    ) -> None:
        if speed < 0:
            raise ValueError("speed must be non-negative")
        self._position = position
        self._speed = float(speed)
        self._bounds = bounds
        self._direction = direction
        self._state = MovementState.IDLE
        self._previous_state = MovementState.IDLE

    @property
    def position(self) -> WorldPosition:
        return self._position

    @property
    def bounds(self) -> MovementBounds:
        return self._bounds

    @property
    def speed(self) -> float:
        return self._speed

    @property
    def direction(self) -> Direction:
        return self._direction

    @property
    def state(self) -> MovementState:
        return self._state

    def set_direction(self, direction: Direction) -> None:
        self._direction = direction

    def set_position(self, position: WorldPosition) -> WorldPosition:
        """Move the model directly (e.g. after a user drag), clamped to bounds.

        Kept as a public, Qt-free operation so the interaction layer never
        touches private state.
        """
        self._position = self._bounds.clamp(position)
        return self._position

    def velocity(self) -> tuple[float, float]:
        if self._state is not MovementState.WALKING:
            return (0.0, 0.0)
        vx, vy = self._direction.value
        return (vx * self._speed, vy * self._speed)

    def start(self, direction: Optional[Direction] = None) -> None:
        if direction is not None:
            self._direction = direction
        self._state = MovementState.WALKING
        self._previous_state = MovementState.WALKING

    def stop(self) -> None:
        self._state = MovementState.IDLE
        self._previous_state = MovementState.IDLE

    def pause(self) -> None:
        if self._state is MovementState.WALKING:
            self._previous_state = MovementState.WALKING
            self._state = MovementState.PAUSED

    def resume(self) -> None:
        if self._state is MovementState.PAUSED:
            self._state = (
                self._previous_state
                if self._previous_state is MovementState.WALKING
                else MovementState.WALKING
            )

    def advance(self, delta_time: float) -> bool:
        """Advance by ``delta_time`` seconds. Returns True if position changed."""
        if self._state is not MovementState.WALKING or delta_time <= 0:
            return False
        vx, vy = self.velocity()
        target = self._position.translated(vx * delta_time, vy * delta_time)
        clamped = self._bounds.clamp(target)
        changed = clamped != self._position
        self._position = clamped
        if clamped != target:
            self._state = MovementState.IDLE
            self._previous_state = MovementState.IDLE
        return changed
