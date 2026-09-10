from __future__ import annotations

import math
from enum import Enum
from typing import Callable, Optional, Protocol

from movement.bounds import MovementBounds
from movement.position import WorldPosition


class InteractionState(Enum):
    IDLE = "idle"
    DRAGGING = "dragging"


class SupportsPositioning(Protocol):
    def set_position(self, x: float, y: float) -> bool: ...


class SupportsMovement(Protocol):
    @property
    def is_running(self) -> bool: ...

    def pause(self) -> None: ...

    def resume(self) -> None: ...


class InteractionController:
    """Maps pointer interaction to WorldPosition changes.

    Plain Python: no Qt, no widgets, no platform code. The window emits raw
    pointer coordinates; this controller decides what they mean (click vs drag)
    and delegates the actual window placement to a ``PositioningService``.
    """

    def __init__(
        self,
        *,
        bounds: MovementBounds,
        positioning: Optional[SupportsPositioning] = None,
        movement: Optional[SupportsMovement] = None,
        model=None,
        click_threshold: float = 4.0,
        enabled: bool = True,
        on_press: Optional[Callable[[float, float], None]] = None,
        on_click: Optional[Callable[[float, float], None]] = None,
        on_drag_start: Optional[Callable[[WorldPosition], None]] = None,
        on_drag_move: Optional[Callable[[WorldPosition], None]] = None,
        on_drag_end: Optional[Callable[[WorldPosition], None]] = None,
    ) -> None:
        self._bounds = bounds
        self._positioning = positioning
        self._movement = movement
        self._model = model
        self._click_threshold = float(click_threshold)
        self.enabled = bool(enabled)
        self.on_press = on_press
        self.on_click = on_click
        self.on_drag_start = on_drag_start
        self.on_drag_move = on_drag_move
        self.on_drag_end = on_drag_end

        self._state = InteractionState.IDLE
        self._offset = (0.0, 0.0)
        self._press = (0.0, 0.0)
        self._travelled = 0.0
        self._resume_after = False
        self._drag_started = False
        self._last_position: Optional[WorldPosition] = None

    @property
    def state(self) -> InteractionState:
        return self._state

    @property
    def is_dragging(self) -> bool:
        return self._state is InteractionState.DRAGGING

    def handle_press(self, global_x: float, global_y: float, world_position: WorldPosition) -> None:
        if not self.enabled:
            return
        self._press = (global_x, global_y)
        self._offset = (global_x - world_position.x, global_y - world_position.y)
        self._travelled = 0.0
        self._drag_started = False
        self._last_position = world_position
        self._state = InteractionState.DRAGGING
        if self._movement is not None and self._movement.is_running:
            self._resume_after = True
            self._movement.pause()
        else:
            self._resume_after = False
        if self.on_press is not None:
            self.on_press(global_x, global_y)

    def handle_move(self, global_x: float, global_y: float) -> None:
        if not self.enabled or self._state is not InteractionState.DRAGGING:
            return
        travelled = math.hypot(global_x - self._press[0], global_y - self._press[1])
        self._travelled = max(self._travelled, travelled)
        target = WorldPosition(global_x - self._offset[0], global_y - self._offset[1])
        clamped = self._bounds.clamp(target)
        self._last_position = clamped
        if self._model is not None:
            self._model.set_position(clamped)
        if self._positioning is not None:
            self._positioning.set_position(clamped.x, clamped.y)
        if not self._drag_started and self._travelled > self._click_threshold:
            self._drag_started = True
            if self.on_drag_start is not None:
                self.on_drag_start(clamped)
        if self.on_drag_move is not None:
            self.on_drag_move(clamped)

    def handle_release(self, global_x: float, global_y: float) -> None:
        if not self.enabled or self._state is not InteractionState.DRAGGING:
            return
        self.handle_move(global_x, global_y)
        position = self._last_position or WorldPosition(global_x, global_y)
        was_drag = self._drag_started
        self._state = InteractionState.IDLE
        self._drag_started = False

        if self._resume_after:
            if self._movement is not None:
                self._movement.resume()
        elif self._model is not None:
            self._model.stop()
        self._resume_after = False

        if was_drag:
            if self.on_drag_end is not None:
                self.on_drag_end(position)
        elif self.on_click is not None:
            self.on_click(global_x, global_y)
