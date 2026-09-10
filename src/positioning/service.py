from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

NATIVE_WAYLAND = "wayland"


def supports_physical_positioning(platform_name: str) -> bool:
    """Return whether the platform honors absolute top-level window placement.

    Native Wayland compositors ignore ``move()`` for ordinary applications, so
    physical positioning is unsupported there even though logical movement
    still works. X11/XWayland (``xcb``) and the offscreen/minimal platforms
    honor it.
    """
    return (platform_name or "").strip().lower() != NATIVE_WAYLAND


@runtime_checkable
class PositioningService(Protocol):
    """Platform window-positioning contract.

    Implementations answer "can the window actually be moved here?" and apply
    positions when possible. They must never report success when the platform
    ignored the request.
    """

    def platform_name(self) -> str: ...

    def supports_physical_positioning(self) -> bool: ...

    def set_position(self, x: float, y: float) -> bool: ...


class LogicalOnlyPositioning:
    """Records requested positions without touching any real window.

    Used for platforms that cannot physically position windows and as a pure
    test double. ``set_position`` deliberately returns ``False`` so callers
    cannot mistake a logical update for a physical move.
    """

    def __init__(self, platform_name: str = NATIVE_WAYLAND) -> None:
        self._platform_name = platform_name
        self.last_position: Optional[tuple[float, float]] = None

    def platform_name(self) -> str:
        return self._platform_name

    def supports_physical_positioning(self) -> bool:
        return False

    def set_position(self, x: float, y: float) -> bool:
        self.last_position = (float(x), float(y))
        return False
