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

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from animation.asset_loader import AssetDiscovery  # noqa: E402
from animation.controller import AnimationController  # noqa: E402
from animation.idle import IdleAnimation  # noqa: E402
from config.settings import Config  # noqa: E402
from ui.desktop_window import DesktopWindow  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Desktop Pet (phase 1)")
    parser.add_argument("--config", type=Path, default=None, help="path to config.yaml")
    parser.add_argument("--screenshot", type=Path, default=None, help="render one frame, save PNG and exit")
    parser.add_argument("--screenshot-delay", type=float, default=1.0, help="seconds before single screenshot")
    parser.add_argument(
        "--screenshot-seq",
        type=Path,
        default=None,
        help="capture a sequence of frames into this directory, then exit",
    )
    parser.add_argument("--frame-count", type=int, default=4, help="frames captured with --screenshot-seq")
    parser.add_argument("--frame-interval", type=float, default=0.5, help="seconds between sequence frames")
    parser.add_argument("--run-seconds", type=float, default=None, help="auto-quit after N seconds")
    parser.add_argument("--no-animation", action="store_true", help="disable animation for this run")
    parser.add_argument("--pause-at", type=float, default=None, help="pause animation N seconds after start")
    parser.add_argument("--resume-at", type=float, default=None, help="resume animation N seconds after start")
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


def build_animation(config: Config, render_height: int, logger: logging.Logger):
    if not config.animation.enabled or not config.animation.idle.enabled:
        logger.info("idle animation disabled by config")
        return None, 0
    idle_cfg = config.animation.idle
    animation = IdleAnimation(
        duration=idle_cfg.duration,
        float_amplitude=idle_cfg.float_amplitude,
        scale_amplitude=idle_cfg.scale_amplitude,
        rotation_amplitude=idle_cfg.rotation_amplitude,
    )
    padding = animation.render_padding(render_height)
    logger.info(
        "idle animation: duration=%s float=%s scale=%s rotation=%s padding=%spx fps=%s",
        idle_cfg.duration,
        idle_cfg.float_amplitude,
        idle_cfg.scale_amplitude,
        idle_cfg.rotation_amplitude,
        padding,
        config.animation.fps,
    )
    return animation, padding


def main() -> int:
    args = parse_args()
    logger = setup_logging()
    config = Config.load(args.config)
    if args.no_animation:
        config.animation.enabled = False
    logger.info(
        "config loaded: walk_speed=%s idle_time=%s window_scale=%s behavior_enabled=%s",
        config.walk_speed,
        config.idle_time,
        config.window_scale,
        config.behavior_enabled,
    )
    describe_environment(logger)
    resolve_platform(config, logger)

    app = QApplication(sys.argv[:1])
    app.setApplicationName("Desktop Pet")

    discovery = AssetDiscovery(
        generated_root=config.generated_root_path,
        original_root=config.original_root_path,
        fallback=config.fallback_path,
    )
    frame = discovery.first_frame()
    logger.info("using frame: %s", frame)

    render_height = max(1, int(config.window.pet_height * config.window_scale))
    animation, padding = build_animation(config, render_height, logger)

    window = DesktopWindow(config, frame, padding=padding)
    window.show()
    logger.info(
        "window shown: size=%sx%s pos=(%s,%s)",
        window.width(),
        window.height(),
        window.x(),
        window.y(),
    )

    controller = None
    if animation is not None:
        controller = AnimationController(animation, fps=config.animation.fps, parent=window)
        controller.frame_changed.connect(window.set_animation_transform)
        controller.start()
        logger.info("animation started (fps=%.1f)", controller.fps)

        if args.pause_at is not None:
            def do_pause() -> None:
                controller.pause()
                logger.info("animation paused at t=%.2fs", args.pause_at)

            QTimer.singleShot(int(args.pause_at * 1000), do_pause)

        if args.resume_at is not None:
            def do_resume() -> None:
                controller.resume()
                logger.info("animation resumed at t=%.2fs", args.resume_at)

            QTimer.singleShot(int(args.resume_at * 1000), do_resume)

    if args.screenshot:
        out = Path(args.screenshot)

        def capture() -> None:
            out.parent.mkdir(parents=True, exist_ok=True)
            window.grab().save(str(out))
            logger.info("screenshot saved: %s", out)
            app.quit()

        QTimer.singleShot(int(args.screenshot_delay * 1000), capture)

    if args.screenshot_seq:
        out_dir = Path(args.screenshot_seq)
        out_dir.mkdir(parents=True, exist_ok=True)
        total = max(1, int(args.frame_count))
        interval_ms = max(1, int(args.frame_interval * 1000))

        def capture_sequence(index: int) -> None:
            target = out_dir / f"frame_{index:02d}.png"
            window.grab().save(str(target))
            logger.info("sequence frame %s/%s saved: %s", index + 1, total, target)
            if index + 1 < total:
                QTimer.singleShot(interval_ms, lambda: capture_sequence(index + 1))
            else:
                app.quit()

        QTimer.singleShot(int(args.screenshot_delay * 1000), lambda: capture_sequence(0))

    if args.run_seconds:
        QTimer.singleShot(int(args.run_seconds * 1000), app.quit)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
