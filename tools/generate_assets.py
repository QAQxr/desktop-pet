"""Generate derived (placeholder) pet assets from read-only original artwork.

This script NEVER writes to picture/original/. It reads the original
character portrait and produces a background-removed RGBA frame under
picture/generated/. The output is explicitly labelled as generated /
placeholder so it is never mistaken for an official animation frame.

Usage:
    python tools/generate_assets.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from animation.background import remove_background  # noqa: E402

ORIGINAL_DIR = PROJECT_ROOT / "picture" / "original"
GENERATED_DIR = PROJECT_ROOT / "picture" / "generated"
SOURCE_CANDIDATES = ["file.png", "file", "素材.png"]


def _find_source() -> Path:
    for name in SOURCE_CANDIDATES:
        candidate = ORIGINAL_DIR / name
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"no original artwork found in {ORIGINAL_DIR}")


def main() -> None:
    source = _find_source()
    print(f"source (read-only): {source.relative_to(PROJECT_ROOT)}")

    idle_dir = GENERATED_DIR / "character" / "idle"
    idle_dir.mkdir(parents=True, exist_ok=True)

    with Image.open(source) as raw:
        frame = remove_background(raw)
    out = idle_dir / "idle_00.png"
    frame.save(out)
    print(f"generated: {out.relative_to(PROJECT_ROOT)} size={frame.size}")

    manifest_path = GENERATED_DIR / "MANIFEST.json"
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "tools/generate_assets.py",
        "classification": "generated / placeholder",
        "warning": "Not official animation frames. Replace with real frames in picture/generated/character/<action>/.",
        "sources": [str(source.relative_to(PROJECT_ROOT))],
        "outputs": [
            {
                "path": str(out.relative_to(PROJECT_ROOT)),
                "action": "idle",
                "direction": None,
                "index": 0,
                "note": "background-removed placeholder derived from original portrait",
            }
        ],
        "naming_convention": "<action>[_<left|right>]_<NN>.png",
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest: {manifest_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
