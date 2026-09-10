import sys
import unittest
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from animation.asset_loader import FRAME_RE, AssetDiscovery  # noqa: E402
from animation.background import remove_background  # noqa: E402
from config.settings import Config  # noqa: E402


class ConfigTest(unittest.TestCase):
    def test_loads_declared_values(self):
        cfg = Config.load(PROJECT_ROOT / "config" / "config.yaml")
        self.assertEqual(cfg.walk_speed, 80.0)
        self.assertEqual(cfg.idle_time, 5.0)
        self.assertTrue(cfg.behavior_enabled)
        self.assertTrue(str(cfg.generated_root_path).endswith("picture/generated"))
        self.assertTrue(str(cfg.original_root_path).endswith("picture/original"))

    def test_unknown_keys_are_ignored(self):
        cfg = Config.from_dict({"walk_speed": 120, "window": {"nope": 1, "pet_height": 100}})
        self.assertEqual(cfg.walk_speed, 120.0)
        self.assertEqual(cfg.window.pet_height, 100)


class BackgroundTest(unittest.TestCase):
    def test_white_corner_becomes_transparent(self):
        img = Image.new("RGB", (60, 60), (255, 255, 255))
        for x in range(20, 40):
            for y in range(20, 40):
                img.putpixel((x, y), (200, 30, 30))
        out = remove_background(img, pad=0, trim=False)
        self.assertEqual(out.mode, "RGBA")
        self.assertEqual(out.getpixel((0, 0))[3], 0)
        self.assertEqual(out.getpixel((out.width - 1, 0))[3], 0)
        cx, cy = out.width // 2, out.height // 2
        self.assertGreater(out.getpixel((cx, cy))[3], 200)


class FrameRegexTest(unittest.TestCase):
    def test_naming_convention(self):
        match = FRAME_RE.match("walk_right_01.png")
        self.assertEqual(match.group("action"), "walk")
        self.assertEqual(match.group("direction"), "right")
        self.assertEqual(match.group("index"), "01")
        self.assertIsNotNone(FRAME_RE.match("idle_00.png"))
        self.assertIsNone(FRAME_RE.match("random.png"))

    def test_discovery_falls_back_and_finds_idle(self):
        cfg = Config.load(PROJECT_ROOT / "config" / "config.yaml")
        discovery = AssetDiscovery(
            cfg.generated_root_path, cfg.original_root_path, cfg.fallback_path
        )
        frame = discovery.first_frame()
        self.assertTrue(frame.exists())
        self.assertTrue(frame.name.startswith("idle_"))


if __name__ == "__main__":
    unittest.main()
