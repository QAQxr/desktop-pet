from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorldPosition:
    """The pet window's real position on the desktop, in pixels.

    Kept separate from ``AnimationTransform`` (in-memory visual offset) and
    from the rendered result. Movement mutates this; animation never does.
    """

    x: float
    y: float

    def translated(self, dx: float, dy: float) -> "WorldPosition":
        return WorldPosition(self.x + dx, self.y + dy)

    def as_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)
