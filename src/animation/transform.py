from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AnimationTransform:
    """Visual offset produced by an animation.

    This is deliberately separate from the pet's world position: the window
    owns the real on-screen location, while this transform only describes the
    in-memory visual offset (breathing, bobbing, ...). The two must never be
    conflated, otherwise movement and idle motion would fight each other.
    """

    dx: float = 0.0
    dy: float = 0.0
    scale: float = 1.0
    rotation: float = 0.0
    alpha: float = 1.0

    @classmethod
    def identity(cls) -> "AnimationTransform":
        return cls()
