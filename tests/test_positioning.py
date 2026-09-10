import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movement.bounds import MovementBounds  # noqa: E402
from movement.movement import Direction, MovementModel  # noqa: E402
from movement.position import WorldPosition  # noqa: E402
from positioning.qt import QtPositioningService  # noqa: E402
from positioning.service import (  # noqa: E402
    LogicalOnlyPositioning,
    PositioningService,
    supports_physical_positioning,
)

BOUNDS = MovementBounds(min_x=0.0, min_y=0.0, max_x=1000.0, max_y=500.0)


class FakeWindow:
    def __init__(self):
        self.moves = []

    def move(self, x, y):
        self.moves.append((x, y))


class CapabilityTest(unittest.TestCase):
    def test_xcb_supports(self):
        self.assertTrue(supports_physical_positioning("xcb"))

    def test_native_wayland_does_not_support(self):
        self.assertFalse(supports_physical_positioning("wayland"))

    def test_offscreen_supports(self):
        self.assertTrue(supports_physical_positioning("offscreen"))

    def test_case_insensitive(self):
        self.assertFalse(supports_physical_positioning("Wayland"))
        self.assertFalse(supports_physical_positioning(" WAYLAND "))

    def test_empty_is_treated_as_supported(self):
        self.assertTrue(supports_physical_positioning(""))


class QtPositioningServiceTest(unittest.TestCase):
    def test_xcb_applies_position(self):
        window = FakeWindow()
        service = QtPositioningService(window, "xcb")
        self.assertTrue(service.supports_physical_positioning())
        self.assertEqual(service.platform_name(), "xcb")
        self.assertTrue(service.set_position(10.4, 20.4))
        self.assertEqual(window.moves, [(10, 20)])

    def test_native_wayland_refuses_and_does_not_move(self):
        window = FakeWindow()
        service = QtPositioningService(window, "wayland")
        self.assertFalse(service.supports_physical_positioning())
        self.assertFalse(service.set_position(300.0, 400.0))
        self.assertEqual(window.moves, [])

    def test_satisfies_protocol(self):
        service = QtPositioningService(FakeWindow(), "xcb")
        self.assertIsInstance(service, PositioningService)


class LogicalOnlyPositioningTest(unittest.TestCase):
    def test_records_but_never_claims_success(self):
        service = LogicalOnlyPositioning()
        self.assertFalse(service.supports_physical_positioning())
        self.assertFalse(service.set_position(5.0, 6.0))
        self.assertEqual(service.last_position, (5.0, 6.0))


class DecouplingTest(unittest.TestCase):
    def test_positioning_layer_does_not_import_movement(self):
        source = (PROJECT_ROOT / "src" / "positioning" / "service.py").read_text(encoding="utf-8")
        self.assertNotIn("import movement", source)
        self.assertNotIn("from movement", source)

    def test_movement_layer_does_not_import_positioning(self):
        source = (PROJECT_ROOT / "src" / "movement" / "movement.py").read_text(encoding="utf-8")
        self.assertNotIn("import positioning", source)
        self.assertNotIn("from positioning", source)

    def test_movement_works_without_positioning(self):
        model = MovementModel(WorldPosition(0.0, 0.0), 100.0, BOUNDS, Direction.RIGHT)
        model.start()
        model.advance(1.0)
        self.assertAlmostEqual(model.position.x, 100.0)

    def test_positioning_works_without_movement(self):
        window = FakeWindow()
        service = QtPositioningService(window, "xcb")
        service.set_position(42.0, 24.0)
        self.assertEqual(window.moves, [(42, 24)])


if __name__ == "__main__":
    unittest.main()
