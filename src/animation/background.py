from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

WHITE_THRESHOLD = 232
FEATHER_RADIUS = 0.6


def scanline_flood(white: np.ndarray, seeds: list[tuple[int, int]]) -> np.ndarray:
    h, w = white.shape
    filled = np.zeros((h, w), dtype=bool)
    stack = list(seeds)
    while stack:
        y, x = stack.pop()
        if y < 0 or y >= h or x < 0 or x >= w:
            continue
        if filled[y, x] or not white[y, x]:
            continue
        xl = x
        while xl - 1 >= 0 and white[y, xl - 1] and not filled[y, xl - 1]:
            xl -= 1
        xr = x
        while xr + 1 < w and white[y, xr + 1] and not filled[y, xr + 1]:
            xr += 1
        filled[y, xl:xr + 1] = True
        for ny in (y - 1, y + 1):
            if 0 <= ny < h:
                seg = white[ny, xl:xr + 1] & ~filled[ny, xl:xr + 1]
                idx = np.flatnonzero(seg)
                if idx.size:
                    breaks = np.flatnonzero(np.diff(idx) > 1)
                    starts = np.concatenate(([idx[0]], idx[breaks + 1]))
                    for start in starts:
                        stack.append((ny, int(xl + start)))
    return filled


def remove_background(
    image: Image.Image,
    threshold: int = WHITE_THRESHOLD,
    feather: float = FEATHER_RADIUS,
    pad: int = 8,
    trim: bool = True,
) -> Image.Image:
    rgb = np.asarray(image.convert("RGB")).astype(np.int16)
    white = rgb.min(axis=2) >= threshold

    h, w = white.shape
    seeds: list[tuple[int, int]] = []
    seeds.extend((0, x) for x in range(w) if white[0, x])
    seeds.extend((h - 1, x) for x in range(w) if white[h - 1, x])
    seeds.extend((y, 0) for y in range(h) if white[y, 0])
    seeds.extend((y, w - 1) for y in range(h) if white[y, w - 1])
    removed = scanline_flood(white, seeds)

    rgba = np.asarray(image.convert("RGBA")).copy()
    alpha = np.where(removed, 0, 255).astype(np.uint8)
    if feather > 0:
        alpha = np.array(
            Image.fromarray(alpha, "L").filter(ImageFilter.GaussianBlur(feather))
        )
    alpha[removed] = 0
    rgba[..., 3] = alpha

    result = Image.fromarray(rgba, "RGBA")
    bbox = result.getchannel("A").getbbox()
    if trim and bbox:
        left = max(bbox[0] - pad, 0)
        top = max(bbox[1] - pad, 0)
        right = min(bbox[2] + pad, result.width)
        bottom = min(bbox[3] + pad, result.height)
        result = result.crop((left, top, right, bottom))
    return result
