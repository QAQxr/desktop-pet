from __future__ import annotations

import math

from .transform import AnimationTransform


def idle_transform(
    t: float,
    *,
    duration: float,
    float_amplitude: float,
    scale_amplitude: float,
    rotation_amplitude: float = 0.0,
) -> AnimationTransform:
    """Pure time -> visual-offset function for the idle animation.

    A single sine wave drives both the vertical bob and the subtle scale
    change so the character reads as gently breathing. Raising the character
    while it slightly grows mimics an inhale.
    """
    if duration <= 0:
        raise ValueError("duration must be positive")
    phase = 2.0 * math.pi * ((t / duration) % 1.0)
    wave = math.sin(phase)
    return AnimationTransform(
        dx=0.0,
        dy=-float_amplitude * wave,
        scale=1.0 + scale_amplitude * wave,
        rotation=rotation_amplitude * wave,
        alpha=1.0,
    )


class IdleAnimation:
    """In-memory idle animation derived from a single static frame."""

    name = "idle"

    def __init__(
        self,
        duration: float = 3.0,
        float_amplitude: float = 2.0,
        scale_amplitude: float = 0.01,
        rotation_amplitude: float = 0.0,
    ) -> None:
        if duration <= 0:
            raise ValueError("duration must be positive")
        self.duration = float(duration)
        self.float_amplitude = float(float_amplitude)
        self.scale_amplitude = float(scale_amplitude)
        self.rotation_amplitude = float(rotation_amplitude)

    def sample(self, t: float) -> AnimationTransform:
        return idle_transform(
            t,
            duration=self.duration,
            float_amplitude=self.float_amplitude,
            scale_amplitude=self.scale_amplitude,
            rotation_amplitude=self.rotation_amplitude,
        )

    def render_padding(self, sprite_height: int) -> int:
        """Extra window margin needed so the motion is never clipped."""
        return int(
            math.ceil(abs(self.float_amplitude) + sprite_height * abs(self.scale_amplitude) + 4)
        )
