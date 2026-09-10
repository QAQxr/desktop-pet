from __future__ import annotations

from typing import Optional

from .service import supports_physical_positioning


class QtPositioningService:
    """Positions a Qt widget when the platform allows it.

    Depends only on a duck-typed ``window`` exposing ``move(x, y)``; it never
    imports window/rendering code, so it stays a thin platform adapter.
    """

    def __init__(self, window, platform_name: Optional[str] = None) -> None:
        self._window = window
        self._platform_name = platform_name if platform_name is not None else _detect_platform()

    def platform_name(self) -> str:
        return self._platform_name

    def supports_physical_positioning(self) -> bool:
        return supports_physical_positioning(self._platform_name)

    def set_position(self, x: float, y: float) -> bool:
        if not self.supports_physical_positioning():
            return False
        self._window.move(int(round(x)), int(round(y)))
        return True


def _detect_platform() -> str:
    from PySide6.QtGui import QGuiApplication

    return QGuiApplication.platformName()
