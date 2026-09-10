import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from animation.clock import AnimationClock  # noqa: E402
from animation.idle import IdleAnimation, idle_transform  # noqa: E402
from animation.transform import AnimationTransform  # noqa: E402
from config.settings import Config  # noqa: E402


class IdleMathTest(unittest.TestCase):
    def test_key_points(self):
        amp, samp = 2.0, 0.01
        rest = idle_transform(0.0, duration=4.0, float_amplitude=amp, scale_amplitude=samp)
        self.assertAlmostEqual(rest.dy, 0.0, places=6)
        self.assertAlmostEqual(rest.scale, 1.0, places=6)
        peak = idle_transform(1.0, duration=4.0, float_amplitude=amp, scale_amplitude=samp)
        self.assertAlmostEqual(peak.dy, -amp, places=6)
        self.assertAlmostEqual(peak.scale, 1.0 + samp, places=6)
        trough = idle_transform(3.0, duration=4.0, float_amplitude=amp, scale_amplitude=samp)
        self.assertAlmostEqual(trough.dy, amp, places=6)

    def test_periodic(self):
        first = idle_transform(0.37, duration=3.0, float_amplitude=2.0, scale_amplitude=0.01)
        second = idle_transform(3.37, duration=3.0, float_amplitude=2.0, scale_amplitude=0.01)
        self.assertAlmostEqual(first.dy, second.dy, places=9)
        self.assertAlmostEqual(first.scale, second.scale, places=9)

    def test_alpha_constant(self):
        for t in (0.0, 0.7, 1.5, 2.9):
            transform = idle_transform(
                t, duration=3.0, float_amplitude=2.0, scale_amplitude=0.01
            )
            self.assertEqual(transform.alpha, 1.0)

    def test_invalid_duration(self):
        with self.assertRaises(ValueError):
            idle_transform(0.0, duration=0.0, float_amplitude=1.0, scale_amplitude=0.0)


class ClockTest(unittest.TestCase):
    def test_pause_freezes_and_resume_continues(self):
        clock = AnimationClock()
        clock.start(100.0)
        self.assertAlmostEqual(clock.time(100.0), 0.0)
        self.assertAlmostEqual(clock.time(101.0), 1.0)
        clock.pause(101.5)
        self.assertTrue(clock.paused)
        self.assertAlmostEqual(clock.time(105.0), 1.5)
        clock.resume(105.0)
        self.assertFalse(clock.paused)
        self.assertAlmostEqual(clock.time(105.0), 1.5)
        self.assertAlmostEqual(clock.time(106.0), 2.5)

    def test_stop_resets(self):
        clock = AnimationClock()
        clock.start(0.0)
        clock.time(5.0)
        clock.stop()
        self.assertFalse(clock.running)
        self.assertEqual(clock.time(10.0), 0.0)


class AnimationConfigTest(unittest.TestCase):
    def test_loads_from_config(self):
        cfg = Config.load(PROJECT_ROOT / "config" / "config.yaml")
        self.assertTrue(cfg.animation.enabled)
        self.assertEqual(cfg.animation.fps, 30)
        self.assertTrue(cfg.animation.idle.enabled)
        self.assertEqual(cfg.animation.idle.duration, 3.0)
        self.assertEqual(cfg.animation.idle.float_amplitude, 2.0)
        self.assertEqual(cfg.animation.idle.scale_amplitude, 0.01)

    def test_defaults_when_missing(self):
        cfg = Config.from_dict({})
        self.assertTrue(cfg.animation.enabled)
        self.assertEqual(cfg.animation.idle.duration, 3.0)


class IdleAnimationObjectTest(unittest.TestCase):
    def test_render_padding_positive(self):
        animation = IdleAnimation(duration=3.0, float_amplitude=2.0, scale_amplitude=0.01)
        self.assertGreaterEqual(animation.render_padding(220), 4)

    def test_does_not_write_files(self):
        generated = PROJECT_ROOT / "picture" / "generated"
        before = {str(p) for p in generated.rglob("*")} if generated.exists() else set()
        animation = IdleAnimation()
        for step in range(50):
            animation.sample(step * 0.05)
        after = {str(p) for p in generated.rglob("*")} if generated.exists() else set()
        self.assertEqual(before, after)


class ControllerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def test_start_pause_resume_stop(self):
        from animation.controller import AnimationController

        controller = AnimationController(IdleAnimation(), fps=60)
        emitted = []
        controller.frame_changed.connect(lambda transform: emitted.append(transform))
        controller.start()
        self.assertTrue(controller.is_running)
        self.assertFalse(controller.is_paused)
        self.assertTrue(emitted)
        controller.pause()
        self.assertTrue(controller.is_paused)
        self.assertFalse(controller.is_running)
        controller.resume()
        self.assertTrue(controller.is_running)
        self.assertFalse(controller.is_paused)
        controller.stop()
        self.assertFalse(controller.is_running)
        self.assertEqual(controller.current(), AnimationTransform.identity())


if __name__ == "__main__":
    unittest.main()
