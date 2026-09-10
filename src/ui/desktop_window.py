from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QGuiApplication, QPainter, QPixmap
from PySide6.QtWidgets import QWidget

from animation.transform import AnimationTransform
from config.settings import Config


class DesktopWindow(QWidget):
    """Frameless, background-transparent window that renders the pet sprite.

    The window owns the pet's real (world) position. It receives a visual
    ``AnimationTransform`` from the animation layer and applies it only while
    painting, so animation offsets never move the actual window.
    """

    def __init__(
        self,
        config: Config,
        frame_path: Path,
        padding: int = 0,
        parent=None,
    ):
        super().__init__(parent)
        self.config = config
        self._frame_path = Path(frame_path)
        self._padding = max(0, int(padding))
        self._transform = AnimationTransform.identity()
        self.setWindowTitle("Desktop Pet")

        flags = Qt.FramelessWindowHint | Qt.Tool
        if config.window.always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)

        pixmap = QPixmap(str(self._frame_path))
        if pixmap.isNull():
            raise RuntimeError(f"failed to load frame: {self._frame_path}")
        height = max(1, int(config.window.pet_height * config.window_scale))
        self._pixmap = pixmap.scaledToHeight(height, Qt.SmoothTransformation)
        pad = self._padding
        self.resize(self._pixmap.width() + 2 * pad, self._pixmap.height() + 2 * pad)
        self._place_initially()

    def _place_initially(self) -> None:
        start_x = self.config.window.start_x
        start_y = self.config.window.start_y
        if start_x is not None and start_y is not None:
            self.move(int(start_x), int(start_y))
            return
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            self.move(geo.right() - self.width() - 60, geo.bottom() - self.height() - 60)

    def current_frame(self) -> Path:
        return self._frame_path

    def set_animation_transform(self, transform: AnimationTransform) -> None:
        self._transform = transform
        self.update()

    def animation_transform(self) -> AnimationTransform:
        return self._transform

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        transform = self._transform
        painter.setOpacity(max(0.0, min(1.0, transform.alpha)))

        scale = transform.scale
        width = self._pixmap.width() * scale
        height = self._pixmap.height() * scale
        anchor_x = self.width() / 2.0
        anchor_y = self.height() - self._padding
        left = anchor_x - width / 2.0 + transform.dx
        top = anchor_y - height + transform.dy

        if transform.rotation:
            painter.translate(anchor_x, anchor_y)
            painter.rotate(transform.rotation)
            painter.translate(-anchor_x, -anchor_y)

        target = QRectF(left, top, width, height)
        painter.drawPixmap(target, self._pixmap, QRectF(self._pixmap.rect()))
        painter.end()
