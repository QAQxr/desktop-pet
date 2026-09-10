from __future__ import annotations

from dataclasses import dataclass

from .position import WorldPosition


@dataclass(frozen=True)
class MovementBounds:
    """Axis-aligned rectangle the pet window may occupy.

    Bounds are derived from the real screen geometry and the window size, so
    the pet can never leave the visible desktop.
    """

    min_x: float
    min_y: float
    max_x: float
    max_y: float

    def clamp(self, position: WorldPosition) -> WorldPosition:
        x = min(max(position.x, self.min_x), self.max_x)
        y = min(max(position.y, self.min_y), self.max_y)
        return WorldPosition(x, y)

    def contains(self, position: WorldPosition) -> bool:
        return (
            self.min_x <= position.x <= self.max_x
            and self.min_y <= position.y <= self.max_y
        )

    @classmethod
    def from_screen(
        cls,
        screen_left: float,
        screen_top: float,
        screen_width: float,
        screen_height: float,
        window_width: float,
        window_height: float,
    ) -> "MovementBounds":
        max_x = screen_left + screen_width - window_width
        max_y = screen_top + screen_height - window_height
        max_x = max(max_x, screen_left)
        max_y = max(max_y, screen_top)
        return cls(
            min_x=float(screen_left),
            min_y=float(screen_top),
            max_x=float(max_x),
            max_y=float(max_y),
        )
