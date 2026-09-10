from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QPainter, QPixmap
from PySide6.QtWidgets import QWidget

from config.settings import Config


class DesktopWindow(QWidget):
    """Frameless, background-transparent window that hosts the pet sprite.

    The window itself holds no behaviour or animation logic; it only renders
    the current frame. This keeps the window system decoupled from the
    animation and behaviour systems.
    """

    def __init__(self, config: Config, frame_path: Path, parent=None):
        super().__init__(parent)
        self.config = config
        self._frame_path = Path(frame_path)
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
        self.resize(self._pixmap.size())
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

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.drawPixmap(self.rect(), self._pixmap)
        painter.end()
