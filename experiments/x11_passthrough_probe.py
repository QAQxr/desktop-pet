"""Real X11 input-passthrough test using XTEST (no extra dependencies).

Two top-level windows in one app:
  * Background: frameless opaque window, receives clicks in its input region.
  * Pet: frameless translucent window with ``setMask`` (red ellipse), on top.

XTEST synthesizes real pointer clicks at the X server (physical pixels):
  * a point OUTSIDE the pet mask (over the pet window) -> must reach Background
  * a point INSIDE  the pet mask                        -> must reach Pet

Only meaningful on X11/XWayland (run with QT_QPA_PLATFORM=xcb).
"""
from __future__ import annotations

import ctypes
import os
import sys

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QRegion
from PySide6.QtWidgets import QApplication, QWidget

# geometry (device-independent logical pixels)
BG_GEOM = (100, 100, 700, 500)
PET_GEOM = (200, 200, 400, 300)
MASK_LOCAL = QRect(120, 80, 160, 160)  # ellipse inside pet window
OUTSIDE_LOCAL = (25, 25)  # over pet window, outside mask
INSIDE_LOCAL = (MASK_LOCAL.center().x(), MASK_LOCAL.center().y())

_x11 = ctypes.CDLL("libX11.so.6")
_xtst = ctypes.CDLL("libXtst.so.6")
_x11.XOpenDisplay.restype = ctypes.c_void_p
_x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
_x11.XFlush.argtypes = [ctypes.c_void_p]
_x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
_xtst.XTestFakeMotionEvent.argtypes = [
    ctypes.c_void_p,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_ulong,
]
_xtst.XTestFakeButtonEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]


def click(x: int, y: int) -> None:
    display = _x11.XOpenDisplay(None)
    if not display:
        raise RuntimeError("cannot open X display")
    _xtst.XTestFakeMotionEvent(display, 0, x, y, 0)
    _xtst.XTestFakeButtonEvent(display, 1, 1, 0)
    _xtst.XTestFakeButtonEvent(display, 1, 0, 0)
    _x11.XFlush(display)
    _x11.XCloseDisplay(display)


EVENTS: list[tuple[str, tuple[int, int]]] = []


class Background(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("passthrough-bg")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setGeometry(*BG_GEOM)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(40, 90, 140))

    def mousePressEvent(self, event) -> None:
        point = event.globalPosition().toPoint()
        EVENTS.append(("background", (point.x(), point.y())))


class Pet(QWidget):
    def __init__(self, mask: QRegion):
        super().__init__()
        self._mask = mask
        self.setWindowTitle("passthrough-pet")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setGeometry(*PET_GEOM)
        self.setMask(mask)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(220, 60, 60))
        painter.drawEllipse(self._mask.boundingRect())

    def mousePressEvent(self, event) -> None:
        point = event.globalPosition().toPoint()
        EVENTS.append(("pet", (point.x(), point.y())))


def main() -> int:
    if os.environ.get("QT_QPA_PLATFORM") != "xcb":
        print("Run with QT_QPA_PLATFORM=xcb (X11/XWayland) for this test.")
        return 2

    app = QApplication(sys.argv[:1])
    background = Background()
    pet = Pet(QRegion(MASK_LOCAL, QRegion.Ellipse))
    background.show()
    pet.show()
    app.processEvents()

    dpr = pet.devicePixelRatioF()
    inside_logical = pet.mapToGlobal(QPoint(*INSIDE_LOCAL))
    outside_logical = pet.mapToGlobal(QPoint(*OUTSIDE_LOCAL))
    inside_phys = (round(inside_logical.x() * dpr), round(inside_logical.y() * dpr))
    outside_phys = (round(outside_logical.x() * dpr), round(outside_logical.y() * dpr))
    print(f"dpr={dpr}")
    print(f"pet geometry(logical)={pet.geometry().getRect()} bg geometry(logical)={background.geometry().getRect()}")
    print(f"outside logical={outside_logical.toTuple()} physical={outside_phys}")
    print(f"inside  logical={inside_logical.toTuple()} physical={inside_phys}")

    def raise_pet() -> None:
        pet.raise_()

    def do_outside() -> None:
        click(*outside_phys)

    def do_inside() -> None:
        click(*inside_phys)

    def finish() -> None:
        outside_hits = [e for e in EVENTS if e[0] == "background"]
        pet_hits = [e for e in EVENTS if e[0] == "pet"]
        print(f"events={EVENTS}")
        print(f"background_clicks={len(outside_hits)} pet_clicks={len(pet_hits)}")
        print(f"PASSTHROUGH_OUTSIDE={'PASS' if len(outside_hits) >= 1 else 'FAIL'}")
        print(f"PET_RECEIVES_INSIDE={'PASS' if len(pet_hits) >= 1 else 'FAIL'}")
        app.quit()

    QTimer.singleShot(300, raise_pet)
    QTimer.singleShot(900, do_outside)
    QTimer.singleShot(1300, do_inside)
    QTimer.singleShot(1800, finish)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
