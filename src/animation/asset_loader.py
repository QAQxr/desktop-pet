from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

IMAGE_EXTS = {".png", ".webp", ".gif", ".jpg", ".jpeg", ".bmp"}
FRAME_RE = re.compile(
    r"^(?P<action>[a-zA-Z]+)"
    r"(?:_(?P<direction>left|right|front|back))?"
    r"_(?P<index>\d{2,})"
    r"\.(?P<ext>png|webp|gif|jpg|jpeg|bmp)$"
)


@dataclass(frozen=True)
class SpriteFrame:
    path: Path
    action: str
    direction: Optional[str]
    index: int


Sequence = List[SpriteFrame]
SequenceKey = Tuple[str, Optional[str]]


class AssetDiscovery:
    """Discovers animation frames following the naming convention
    ``<action>[_<direction>]_<NN>.<ext>``.

    Generated assets take priority over originals for the same key. The
    original directory is only ever read, never written.
    """

    def __init__(self, generated_root: Path, original_root: Path, fallback: Path):
        self.generated_root = Path(generated_root)
        self.original_root = Path(original_root)
        self.fallback = Path(fallback)

    def scan(self) -> Dict[SequenceKey, Sequence]:
        sequences: Dict[SequenceKey, Sequence] = {}
        for root in (self.original_root, self.generated_root):
            if not root.exists():
                continue
            for path in sorted(root.rglob("*")):
                if not path.is_file() or path.suffix.lower() not in IMAGE_EXTS:
                    continue
                match = FRAME_RE.match(path.name)
                if not match:
                    continue
                key: SequenceKey = (
                    match.group("action").lower(),
                    match.group("direction"),
                )
                sequences.setdefault(key, []).append(
                    SpriteFrame(
                        path=path,
                        action=key[0],
                        direction=key[1],
                        index=int(match.group("index")),
                    )
                )
        for frames in sequences.values():
            frames.sort(key=lambda f: f.index)
        return sequences

    def first_frame(self) -> Path:
        sequences = self.scan()
        for key in (("idle", None), ("idle", "front")):
            if key in sequences:
                return sequences[key][0].path
        for frames in sequences.values():
            if frames:
                return frames[0].path
        if self.fallback.exists():
            return self.fallback
        raise FileNotFoundError(
            "no frames discovered and fallback missing: " + str(self.fallback)
        )
