from __future__ import annotations

import numpy as np
from PySide6.QtGui import QBitmap, QImage, QRegion


def region_from_alpha(pixmap, threshold: int = 1, dilate: int = 0) -> QRegion:
    """Build a QRegion from the pixmap's non-transparent pixels.

    Used both as the widget mask (X11 shape + Wayland input region) so that
    clicks on transparent areas pass through to the application below while
    the character silhouette still receives the pointer.
    """
    image = pixmap.toImage().convertToFormat(QImage.Format_RGBA8888)
    width = image.width()
    height = image.height()
    stride = image.bytesPerLine()
    buffer = np.frombuffer(image.constBits(), dtype=np.uint8)
    buffer = buffer[: height * stride].reshape(height, stride)
    rgba = buffer[:, : width * 4].reshape(height, width, 4)
    # QRegion(QBitmap) treats bit 0 as "inside", so mark transparent pixels
    # with 1; the resulting region is then the opaque (character) area.
    # All-opaque -> all bit 0 -> full region (valid); all-transparent -> empty.
    transparent = rgba[..., 3] <= threshold

    bytes_per_line = ((width + 31) // 32) * 4
    packed = np.zeros((height, bytes_per_line), dtype=np.uint8)
    bits = np.packbits(transparent, axis=1, bitorder="big")
    packed[:, : bits.shape[1]] = bits

    mono = QImage(width, height, QImage.Format_Mono)
    mono.fill(0)
    target = np.frombuffer(mono.bits(), dtype=np.uint8)
    flat = packed.reshape(-1)
    target[: min(target.size, flat.size)] = flat[: target.size]
    region = QRegion(QBitmap.fromImage(mono))
    if dilate > 0:
        region = _dilate(region, int(dilate))
    return region


def _dilate(region: QRegion, pixels: int) -> QRegion:
    result = region
    for dx in range(-pixels, pixels + 1):
        for dy in range(-pixels, pixels + 1):
            if dx == 0 and dy == 0:
                continue
            result = result.united(region.translated(dx, dy))
    return result
