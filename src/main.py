from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from animation.asset_loader import AssetDiscovery  # noqa: E402
from config.settings import Config  # noqa: E402
from ui.desktop_window import DesktopWindow  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Desktop Pet (phase 1)")
    parser.add_argument("--config", type=Path, default=None, help="path to config.yaml")
    parser.add_argument("--screenshot", type=Path, default=None, help="render one frame, save PNG and exit")
    parser.add_argument("--screenshot-delay", type=float, default=1.0, help="seconds before screenshot")
    return parser.parse_args()


def setup_logging() -> logging.Logger:
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"desktop-pet-{datetime.now().strftime('%Y-%m-%d')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler()],
    )
    return logging.getLogger("desktop-pet")


def describe_environment(logger: logging.Logger) -> None:
    for key in ("XDG_SESSION_TYPE", "WAYLAND_DISPLAY", "DISPLAY", "XDG_CURRENT_DESKTOP"):
        logger.info("env %s=%s", key, os.environ.get(key))
    logger.info("env QT_QPA_PLATFORM=%s", os.environ.get("QT_QPA_PLATFORM", "<unset>"))


def resolve_platform(config: Config, logger: logging.Logger) -> None:
    override = config.platform.override or os.environ.get("DESKTOP_PET_QT_PLATFORM")
    if override and "QT_QPA_PLATFORM" not in os.environ:
        os.environ["QT_QPA_PLATFORM"] = override
        logger.info("platform override -> %s", override)
        return
    if "QT_QPA_PLATFORM" in os.environ:
        logger.info("platform already set by environment: %s", os.environ["QT_QPA_PLATFORM"])
        return
    session = os.environ.get("XDG_SESSION_TYPE", "unknown")
    logger.info("session type '%s'; using Qt default platform plugin", session)


def main() -> int:
    args = parse_args()
    logger = setup_logging()
    config = Config.load(args.config)
    logger.info(
        "config loaded: walk_speed=%s idle_time=%s window_scale=%s behavior_enabled=%s",
        config.walk_speed,
        config.idle_time,
        config.window_scale,
        config.behavior_enabled,
    )
    describe_environment(logger)
    resolve_platform(config, logger)

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv[:1])
    app.setApplicationName("Desktop Pet")

    discovery = AssetDiscovery(
        generated_root=config.generated_root_path,
        original_root=config.original_root_path,
        fallback=config.fallback_path,
    )
    frame = discovery.first_frame()
    logger.info("using frame: %s", frame)

    window = DesktopWindow(config, frame)
    window.show()
    logger.info(
        "window shown: size=%sx%s pos=(%s,%s)",
        window.width(),
        window.height(),
        window.x(),
        window.y(),
    )

    if args.screenshot:
        out = Path(args.screenshot)

        def capture() -> None:
            out.parent.mkdir(parents=True, exist_ok=True)
            window.grab().save(str(out))
            logger.info("screenshot saved: %s", out)
            app.quit()

        QTimer.singleShot(int(args.screenshot_delay * 1000), capture)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
