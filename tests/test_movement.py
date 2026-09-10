import hashlib
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from animation.idle import IdleAnimation  # noqa: E402
from animation.transform import AnimationTransform  # noqa: E402
from movement.bounds import MovementBounds  # noqa: E402
from movement.movement import Direction, MovementModel, MovementState  # noqa: E402
from movement.position import WorldPosition  # noqa: E402

BOUNDS = MovementBounds(min_x=0.0, min_y=0.0, max_x=1000.0, max_y=500.0)

ORIGINAL_MD5 = {
    "file": "cb4b06f2d3c7baa84cf56cd536a6d67f",
    "file.png": "6b90177b8fcd2aff8046a1ea87ea9ca2",
    "素材.png": "f7cb1b954578fcd7c3091553c26459f1",
}


class WorldPositionTest(unittest.TestCase):
    def test_translate(self):
        pos = WorldPosition(10.0, 20.0)
        self.assertEqual(pos.translated(5.0, -3.0), WorldPosition(15.0, 17.0))
        self.assertEqual(pos.as_tuple(), (10.0, 20.0))


class BoundsTest(unittest.TestCase):
    def test_clamp_left(self):
        self.assertEqual(BOUNDS.clamp(WorldPosition(-100.0, 10.0)).x, 0.0)

    def test_clamp_right(self):
        self.assertEqual(BOUNDS.clamp(WorldPosition(9999.0, 10.0)).x, 1000.0)

    def test_clamp_top(self):
        self.assertEqual(BOUNDS.clamp(WorldPosition(10.0, -50.0)).y, 0.0)

    def test_clamp_bottom(self):
        self.assertEqual(BOUNDS.clamp(WorldPosition(10.0, 9999.0)).y, 500.0)

    def test_contains(self):
        self.assertTrue(BOUNDS.contains(WorldPosition(500.0, 250.0)))
        self.assertFalse(BOUNDS.contains(WorldPosition(1001.0, 250.0)))

    def test_from_screen_accounts_for_window_size(self):
        bounds = MovementBounds.from_screen(0, 0, 1920, 1080, 220, 240)
        self.assertEqual((bounds.min_x, bounds.min_y), (0.0, 0.0))
        self.assertEqual((bounds.max_x, bounds.max_y), (1700.0, 840.0))


class MovementModelTest(unittest.TestCase):
    def test_delta_time_distance(self):
        model = MovementModel(WorldPosition(0.0, 0.0), speed=100.0, bounds=BOUNDS, direction=Direction.RIGHT)
        model.start()
        model.advance(1.0)
        self.assertAlmostEqual(model.position.x, 100.0)
        self.assertAlmostEqual(model.position.y, 0.0)

    def test_frame_rate_independence(self):
        one_step = MovementModel(WorldPosition(0.0, 0.0), 120.0, BOUNDS, Direction.RIGHT)
        one_step.start()
        one_step.advance(1.0)
        many_steps = MovementModel(WorldPosition(0.0, 0.0), 120.0, BOUNDS, Direction.RIGHT)
        many_steps.start()
        for _ in range(100):
            many_steps.advance(0.01)
        self.assertAlmostEqual(one_step.position.x, many_steps.position.x, places=6)

    def test_left_direction(self):
        model = MovementModel(WorldPosition(500.0, 100.0), 50.0, BOUNDS, Direction.LEFT)
        model.start()
        model.advance(2.0)
        self.assertAlmostEqual(model.position.x, 400.0)

    def test_vertical_direction(self):
        model = MovementModel(WorldPosition(100.0, 100.0), 30.0, BOUNDS, Direction.UP)
        model.start()
        model.advance(1.0)
        self.assertAlmostEqual(model.position.y, 70.0)

    def test_clamps_and_stops_at_boundary(self):
        model = MovementModel(WorldPosition(980.0, 100.0), 200.0, BOUNDS, Direction.RIGHT)
        model.start()
        moved = model.advance(1.0)
        self.assertTrue(moved)
        self.assertAlmostEqual(model.position.x, 1000.0)
        self.assertIs(model.state, MovementState.IDLE)

    def test_pause_prevents_movement(self):
        model = MovementModel(WorldPosition(100.0, 0.0), 100.0, BOUNDS, Direction.RIGHT)
        model.start()
        model.advance(0.5)
        sample = model.position
        model.pause()
        self.assertIs(model.state, MovementState.PAUSED)
        self.assertFalse(model.advance(1.0))
        self.assertEqual(model.position, sample)

    def test_resume_continues(self):
        model = MovementModel(WorldPosition(0.0, 0.0), 100.0, BOUNDS, Direction.RIGHT)
        model.start()
        model.advance(0.5)
        model.pause()
        model.advance(5.0)
        model.resume()
        self.assertIs(model.state, MovementState.WALKING)
        model.advance(0.5)
        self.assertAlmostEqual(model.position.x, 100.0)

    def test_negative_speed_rejected(self):
        with self.assertRaises(ValueError):
            MovementModel(WorldPosition(0.0, 0.0), -1.0, BOUNDS)


class SeparationTest(unittest.TestCase):
    def test_movement_changes_world_position_not_transform(self):
        model = MovementModel(WorldPosition(100.0, 100.0), 60.0, BOUNDS, Direction.RIGHT)
        transform = AnimationTransform.identity()
        model.start()
        model.advance(1.0)
        self.assertNotEqual(model.position, WorldPosition(100.0, 100.0))
        self.assertEqual(transform, AnimationTransform.identity())

    def test_idle_animation_does_not_change_world_position(self):
        model = MovementModel(WorldPosition(50.0, 50.0), 0.0, BOUNDS, Direction.RIGHT)
        before = model.position
        animation = IdleAnimation()
        for step in range(30):
            transform = animation.sample(step * 0.1)
            self.assertEqual(transform.dx, 0.0)
        self.assertEqual(model.position, before)


class MovementConfigTest(unittest.TestCase):
    def test_loads_from_config(self):
        from config.settings import Config

        cfg = Config.load(PROJECT_ROOT / "config" / "config.yaml")
        self.assertTrue(cfg.movement.enabled)
        self.assertEqual(cfg.movement.speed, 120.0)
        self.assertEqual(cfg.movement.direction, "right")
        self.assertEqual(cfg.movement.fps, 60)

    def test_speed_falls_back_to_walk_speed(self):
        from config.settings import Config

        cfg = Config.from_dict({"walk_speed": 77})
        self.assertEqual(cfg.movement.speed, 77.0)


class MovementControllerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def test_start_pause_resume_stop(self):
        from movement.controller import MovementController

        model = MovementModel(WorldPosition(0.0, 0.0), 100.0, BOUNDS, Direction.RIGHT)
        controller = MovementController(model, fps=60)
        controller.start()
        self.assertTrue(controller.is_running)
        self.assertIs(model.state, MovementState.WALKING)
        controller.pause()
        self.assertIs(model.state, MovementState.PAUSED)
        self.assertFalse(controller.is_running)
        controller.resume()
        self.assertIs(model.state, MovementState.WALKING)
        self.assertTrue(controller.is_running)
        controller.stop()
        self.assertIs(model.state, MovementState.IDLE)


class RawAssetProtectionTest(unittest.TestCase):
    def test_original_files_unchanged(self):
        original_dir = PROJECT_ROOT / "picture" / "original"
        for name, expected in ORIGINAL_MD5.items():
            path = original_dir / name
            self.assertTrue(path.exists(), f"missing original: {name}")
            digest = hashlib.md5(path.read_bytes()).hexdigest()
            self.assertEqual(digest, expected, f"original modified: {name}")


if __name__ == "__main__":
    unittest.main()
