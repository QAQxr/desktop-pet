from __future__ import annotations

import argparse
import logging
import math
import os
import signal
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PySide6.QtCore import QElapsedTimer, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from animation.asset_loader import AssetDiscovery  # noqa: E402
from animation.controller import AnimationController  # noqa: E402
from animation.idle import IdleAnimation  # noqa: E402
from config.settings import Config  # noqa: E402
from interaction.controller import InteractionController  # noqa: E402
from movement.bounds import MovementBounds  # noqa: E402
from movement.controller import MovementController  # noqa: E402
from movement.movement import Direction, MovementModel  # noqa: E402
from movement.position import WorldPosition  # noqa: E402
from positioning.qt import QtPositioningService  # noqa: E402
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
    parser.add_argument("--no-interaction", action="store_true", help="disable mouse interaction for this run")
    parser.add_argument("--pause-at", type=float, default=None, help="pause movement+animation N seconds after start")
    parser.add_argument("--resume-at", type=float, default=None, help="resume movement+animation N seconds after start")

    parser.add_argument(
        "--move",
        choices=["left", "right", "up", "down"],
        default=None,
        help="start walking in this direction",
    )
    parser.add_argument(
        "--movement-test",
        action="store_true",
        help="convenience: walk in config direction (default right) for the run",
    )
    parser.add_argument("--no-movement", action="store_true", help="disable movement for this run")
    parser.add_argument("--speed", type=float, default=None, help="override movement speed (pixels/second)")
    parser.add_argument("--start-x", type=int, default=None, help="override initial window x")
    parser.add_argument("--start-y", type=int, default=None, help="override initial window y")
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


def install_signal_handlers(app, logger: logging.Logger) -> None:
    """Quit cleanly on SIGHUP/SIGINT/SIGTERM.

    Ensures that closing the launching terminal (SIGHUP) tears down the Qt
    event loop and window instead of leaving an orphan process behind.
    """

    def handle(signum, frame) -> None:
        name = getattr(signal.Signals(signum), "name", str(signum))
        logger.info("received %s; shutting down", name)
        app.quit()

    for name in ("SIGHUP", "SIGINT", "SIGTERM"):
        sig = getattr(signal, name, None)
        if sig is None:
            continue
        try:
            signal.signal(sig, handle)
        except (ValueError, OSError):
            pass


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


def resolve_direction(args: argparse.Namespace, config: Config):
    if args.move:
        return Direction.from_name(args.move)
    if args.movement_test:
        return Direction.from_name(config.movement.direction)
    return None


def main() -> int:
    args = parse_args()
    logger = setup_logging()
    config = Config.load(args.config)
    if args.no_animation:
        config.animation.enabled = False
    if args.start_x is not None:
        config.window.start_x = args.start_x
    if args.start_y is not None:
        config.window.start_y = args.start_y
    logger.info(
        "config loaded: window_scale=%s behavior_enabled=%s movement.speed=%s interaction.enabled=%s",
        config.window_scale,
        config.behavior_enabled,
        config.movement.speed,
        config.interaction.enabled,
    )
    describe_environment(logger)
    resolve_platform(config, logger)

    app = QApplication(sys.argv[:1])
    app.setApplicationName("Desktop Pet")
    logger.info("Qt platform plugin: %s", app.platformName())
    install_signal_handlers(app, logger)
    app.aboutToQuit.connect(lambda: logger.info("shutting down: Qt event loop exiting"))

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
    app.processEvents()
    logger.info(
        "window shown: size=%sx%s pos=(%s,%s)",
        window.width(),
        window.height(),
        window.x(),
        window.y(),
    )
    region = window.input_region()
    if region is not None:
        logger.info(
            "input mask: rects=%s bounds=%s", region.rectCount(), region.boundingRect().getRect()
        )

    positioning = QtPositioningService(window, app.platformName())
    logger.info(
        "positioning: platform=%s supports_physical_positioning=%s",
        positioning.platform_name(),
        positioning.supports_physical_positioning(),
    )

    animation_controller = None
    if animation is not None:
        animation_controller = AnimationController(animation, fps=config.animation.fps, parent=window)
        animation_controller.frame_changed.connect(window.set_animation_transform)
        animation_controller.start()
        logger.info("animation started (fps=%.1f)", animation_controller.fps)

    screen = window.screen()
    geo = screen.availableGeometry()
    bounds = MovementBounds.from_screen(
        geo.x(), geo.y(), geo.width(), geo.height(), window.width(), window.height()
    )

    direction = resolve_direction(args, config)
    speed = args.speed if args.speed is not None else config.movement.speed
    movement_start = WorldPosition(window.x(), window.y())
    movement_model = MovementModel(
        position=movement_start,
        speed=speed,
        bounds=bounds,
        direction=direction or Direction.RIGHT,
    )
    movement_controller = MovementController(movement_model, fps=config.movement.fps, parent=window)

    trace = {"count": 0}

    def on_position(position: WorldPosition) -> None:
        applied = positioning.set_position(position.x, position.y)
        trace["count"] += 1
        if trace["count"] % max(1, config.movement.fps // 2) == 0:
            logger.info(
                "movement: logical=(%.0f, %.0f) applied=%s state=%s window=(%s,%s)",
                position.x,
                position.y,
                applied,
                movement_model.state.value,
                window.x(),
                window.y(),
            )

    movement_controller.position_changed.connect(on_position)

    auto_move = config.movement.enabled and not args.no_movement and direction is not None
    movement_started_at = QElapsedTimer()

    if auto_move:
        if not positioning.supports_physical_positioning():
            logger.warning(
                "physical window positioning is not available on platform '%s' "
                "(native Wayland). Logical WorldPosition will still update, but the "
                "window will not visibly move. Run with XWayland/X11 for real movement: "
                "QT_QPA_PLATFORM=xcb ./run.sh",
                positioning.platform_name(),
            )
        movement_controller.start()
        movement_started_at.start()
        logger.info(
            "movement started: direction=%s speed=%s fps=%s initial=(%.0f, %.0f) bounds=x[%.0f..%.0f] y[%.0f..%.0f] window_size=%sx%s",
            direction.name,
            speed,
            config.movement.fps,
            movement_start.x,
            movement_start.y,
            bounds.min_x,
            bounds.max_x,
            bounds.min_y,
            bounds.max_y,
            window.width(),
            window.height(),
        )

        def finalize_movement() -> None:
            final = movement_model.position
            elapsed = movement_started_at.elapsed() / 1000.0
            distance = math.hypot(final.x - movement_start.x, final.y - movement_start.y)
            logger.info(
                "movement finished: initial=(%.0f, %.0f) final=(%.0f, %.0f) elapsed=%.2fs distance=%.0fpx state=%s",
                movement_start.x,
                movement_start.y,
                final.x,
                final.y,
                elapsed,
                distance,
                movement_model.state.value,
            )

        app.aboutToQuit.connect(finalize_movement)

    interaction_controller = None
    if config.interaction.enabled and config.interaction.drag_enabled and not args.no_interaction:
        drag_trace = {"count": 0}

        def on_drag_move(pos: WorldPosition) -> None:
            drag_trace["count"] += 1
            if drag_trace["count"] % 6 == 0:
                logger.info("pet drag move world=(%.0f,%.0f)", pos.x, pos.y)

        interaction_controller = InteractionController(
            bounds=bounds,
            positioning=positioning,
            movement=movement_controller,
            model=movement_model,
            click_threshold=config.interaction.click_threshold,
            on_press=lambda gx, gy: logger.info("pet mouse press global=(%.0f,%.0f)", gx, gy),
            on_click=lambda gx, gy: logger.info("pet mouse click global=(%.0f,%.0f)", gx, gy),
            on_drag_start=lambda pos: logger.info("pet drag start world=(%.0f,%.0f)", pos.x, pos.y),
            on_drag_move=on_drag_move,
            on_drag_end=lambda pos: logger.info(
                "pet drag end world=(%.0f,%.0f) state=%s", pos.x, pos.y, movement_model.state.value
            ),
        )
        window.mouse_pressed.connect(
            lambda p: interaction_controller.handle_press(p.x(), p.y(), movement_model.position)
        )
        window.mouse_moved.connect(lambda p: interaction_controller.handle_move(p.x(), p.y()))
        window.mouse_released.connect(lambda p: interaction_controller.handle_release(p.x(), p.y()))
        logger.info(
            "interaction enabled: click_threshold=%s input_mask=%s",
            config.interaction.click_threshold,
            region is not None,
        )
    elif not (config.interaction.enabled and config.interaction.drag_enabled):
        logger.info("interaction disabled by config")

    if args.pause_at is not None:
        def do_pause() -> None:
            if animation_controller is not None:
                animation_controller.pause()
            movement_controller.pause()
            logger.info(
                "paused (animation+movement) at t=%.2fs world=%s",
                args.pause_at,
                movement_model.position.as_tuple(),
            )

        QTimer.singleShot(int(args.pause_at * 1000), do_pause)

    if args.resume_at is not None:
        def do_resume() -> None:
            if animation_controller is not None:
                animation_controller.resume()
            movement_controller.resume()
            logger.info(
                "resumed (animation+movement) at t=%.2fs world=%s",
                args.resume_at,
                movement_model.position.as_tuple(),
            )

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
            transform = window.animation_transform()
            logger.info(
                "sequence frame %s/%s saved: %s world=(%s,%s) anim_dy=%.2f anim_scale=%.3f",
                index + 1,
                total,
                target,
                window.x(),
                window.y(),
                transform.dy,
                transform.scale,
            )
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
