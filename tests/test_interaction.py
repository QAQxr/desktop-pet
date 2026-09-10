import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from interaction.controller import InteractionController, InteractionState  # noqa: E402
from movement.bounds import MovementBounds  # noqa: E402
from movement.position import WorldPosition  # noqa: E402

BOUNDS = MovementBounds(min_x=0.0, min_y=0.0, max_x=1000.0, max_y=500.0)


class FakeModel:
    def __init__(self, position):
        self.position = position
        self.stopped = False
        self.set_calls = []

    def set_position(self, position):
        self.position = position
        self.set_calls.append(position)
        return position

    def stop(self):
        self.stopped = True


class FakeMovement:
    def __init__(self, model, running=True):
        self.model = model
        self._running = running
        self.paused = False
        self.resumed = False

    @property
    def is_running(self):
        return self._running

    def pause(self):
        self.paused = True
        self._running = False

    def resume(self):
        self.resumed = True
        self._running = True


class FakePositioning:
    def __init__(self):
        self.calls = []

    def set_position(self, x, y):
        self.calls.append((x, y))
        return True


def build(**kwargs):
    model = FakeModel(WorldPosition(100.0, 100.0))
    movement = FakeMovement(model, running=kwargs.pop("running", False))
    positioning = FakePositioning()
    events = {"press": 0, "click": 0, "drag_start": 0, "drag_move": 0, "drag_end": 0}
    controller = InteractionController(
        bounds=BOUNDS,
        positioning=positioning,
        movement=movement,
        model=model,
        click_threshold=4.0,
        on_press=lambda gx, gy: events.__setitem__("press", events["press"] + 1),
        on_click=lambda gx, gy: events.__setitem__("click", events["click"] + 1),
        on_drag_start=lambda pos: events.__setitem__("drag_start", events["drag_start"] + 1),
        on_drag_move=lambda pos: events.__setitem__("drag_move", events["drag_move"] + 1),
        on_drag_end=lambda pos: events.__setitem__("drag_end", events["drag_end"] + 1),
        **kwargs,
    )
    return controller, movement, model, positioning, events


class PressMoveReleaseTest(unittest.TestCase):
    def test_press_enters_dragging(self):
        controller, _, _, _, events = build()
        controller.handle_press(110.0, 120.0, WorldPosition(100.0, 100.0))
        self.assertIs(controller.state, InteractionState.DRAGGING)
        self.assertTrue(controller.is_dragging)
        self.assertEqual(events["press"], 1)
        self.assertEqual(events["drag_start"], 0)

    def test_drag_start_fires_only_after_threshold(self):
        controller, _, _, _, events = build()
        controller.handle_press(110.0, 120.0, WorldPosition(100.0, 100.0))
        controller.handle_move(112.0, 121.0)  # < 4px travel
        self.assertEqual(events["drag_start"], 0)
        controller.handle_move(130.0, 130.0)  # > threshold
        self.assertEqual(events["drag_start"], 1)

    def test_move_keeps_offset_without_jump(self):
        controller, _, model, positioning, _ = build()
        controller.handle_press(110.0, 120.0, WorldPosition(100.0, 100.0))  # offset (10,20)
        controller.handle_move(150.0, 170.0)
        self.assertEqual(model.position, WorldPosition(140.0, 150.0))
        self.assertEqual(positioning.calls[-1], (140.0, 150.0))

    def test_no_move_after_release(self):
        controller, _, model, _, _ = build()
        controller.handle_press(110.0, 120.0, WorldPosition(100.0, 100.0))
        controller.handle_move(150.0, 170.0)
        controller.handle_release(150.0, 170.0)
        before = model.position
        controller.handle_move(300.0, 300.0)
        self.assertEqual(model.position, before)
        self.assertIs(controller.state, InteractionState.IDLE)

    def test_small_travel_counts_as_click(self):
        controller, movement, model, _, events = build()
        controller.handle_press(110.0, 120.0, WorldPosition(100.0, 100.0))
        controller.handle_release(111.0, 121.0)
        self.assertEqual(events["click"], 1)
        self.assertEqual(events["drag_end"], 0)
        self.assertTrue(model.stopped)

    def test_large_travel_counts_as_drag(self):
        controller, movement, model, _, events = build()
        controller.handle_press(110.0, 120.0, WorldPosition(100.0, 100.0))
        controller.handle_move(200.0, 200.0)
        controller.handle_release(200.0, 200.0)
        self.assertEqual(events["click"], 0)
        self.assertEqual(events["drag_end"], 1)
        self.assertTrue(model.stopped)

    def test_drag_clamped_to_bounds(self):
        controller, _, model, _, _ = build()
        controller.handle_press(100.0, 100.0, WorldPosition(100.0, 100.0))
        controller.handle_move(5000.0, 5000.0)
        self.assertEqual(model.position, WorldPosition(1000.0, 500.0))
        controller.handle_move(-500.0, -500.0)
        self.assertEqual(model.position, WorldPosition(0.0, 0.0))


class MovementCoordinationTest(unittest.TestCase):
    def test_pauses_then_resumes_running_movement(self):
        controller, movement, model, _, _ = build(running=True)
        controller.handle_press(110.0, 120.0, WorldPosition(100.0, 100.0))
        self.assertTrue(movement.paused)
        self.assertFalse(model.stopped)
        controller.handle_move(200.0, 200.0)
        controller.handle_release(200.0, 200.0)
        self.assertTrue(movement.resumed)

    def test_idle_stays_idle_after_drag(self):
        controller, movement, model, _, _ = build(running=False)
        controller.handle_press(110.0, 120.0, WorldPosition(100.0, 100.0))
        self.assertFalse(movement.paused)
        controller.handle_move(200.0, 200.0)
        controller.handle_release(200.0, 200.0)
        self.assertFalse(movement.resumed)
        self.assertTrue(model.stopped)

    def test_disabled_controller_ignores_events(self):
        controller, movement, model, positioning, events = build(enabled=False)
        controller.handle_press(110.0, 120.0, WorldPosition(100.0, 100.0))
        controller.handle_move(200.0, 200.0)
        controller.handle_release(200.0, 200.0)
        self.assertIs(controller.state, InteractionState.IDLE)
        self.assertEqual(events["press"], 0)
        self.assertEqual(positioning.calls, [])


class DecouplingTest(unittest.TestCase):
    def test_movement_layer_has_no_qt_or_ui_imports(self):
        source = (PROJECT_ROOT / "src" / "movement" / "movement.py").read_text(encoding="utf-8")
        for forbidden in ("PySide6", "import interaction", "from interaction", "import ui", "from ui"):
            self.assertNotIn(forbidden, source)

    def test_interaction_layer_has_no_qt(self):
        source = (PROJECT_ROOT / "src" / "interaction" / "controller.py").read_text(encoding="utf-8")
        self.assertNotIn("PySide6", source)
        self.assertNotIn("QWidget", source)


if __name__ == "__main__":
    unittest.main()
