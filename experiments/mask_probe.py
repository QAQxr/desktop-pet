"""Minimal masked transparent window probe (does not touch DesktopWindow).

Verifies that a Qt window with ``setMask`` maps to a compositor input region:
  * native Wayland: observed via WAYLAND_DEBUG as wl_surface.set_input_region
  * X11/XWayland:  observed via `xwininfo -shape`

Run:
    PROBE_SECONDS=3 python experiments/mask_probe.py
    WAYLAND_DEBUG=1 PROBE_SECONDS=2 python experiments/mask_probe.py 2> wd.log
"""
from __future__ import annotations

import os
import sys

from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QRegion
from PySide6.QtWidgets import QApplication, QWidget


class MaskProbe(QWidget):
    def __init__(self, mask: QRegion):
        super().__init__()
        self._mask = mask
        self.setWindowTitle("mask-probe")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.resize(400, 300)
        self.move(200, 200)
        self.setMask(mask)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(220, 60, 60))
        painter.drawEllipse(self._mask.boundingRect())
        painter.end()


def main() -> int:
    app = QApplication(sys.argv[:1])
    mask = QRegion(QRect(120, 80, 160, 160), QRegion.Ellipse)
    window = MaskProbe(mask)
    window.show()
    app.processEvents()
    print(f"window id: {hex(int(window.winId()))}")
    print(f"mask bounding: {window.mask().boundingRect().getRect()}")
    seconds = float(os.environ.get("PROBE_SECONDS", "3"))
    QTimer.singleShot(int(seconds * 1000), app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
