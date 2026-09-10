from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"


@dataclass
class WindowConfig:
    pet_height: int = 220
    always_on_top: bool = False
    start_x: Optional[int] = None
    start_y: Optional[int] = None


@dataclass
class AssetConfig:
    generated_root: str = "picture/generated"
    original_root: str = "picture/original"
    fallback: str = "picture/original/file.png"


@dataclass
class PlatformConfig:
    override: Optional[str] = None
    prefer_x11_for_positioning: bool = True


@dataclass
class Config:
    walk_speed: float = 80.0
    idle_time: float = 5.0
    window_scale: float = 1.0
    behavior_enabled: bool = True
    window: WindowConfig = field(default_factory=WindowConfig)
    assets: AssetConfig = field(default_factory=AssetConfig)
    platform: PlatformConfig = field(default_factory=PlatformConfig)

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    @property
    def generated_root_path(self) -> Path:
        return PROJECT_ROOT / self.assets.generated_root

    @property
    def original_root_path(self) -> Path:
        return PROJECT_ROOT / self.assets.original_root

    @property
    def fallback_path(self) -> Path:
        return PROJECT_ROOT / self.assets.fallback

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "Config":
        path = Path(path) if path else DEFAULT_CONFIG_PATH
        raw: dict[str, Any] = {}
        if path.exists():
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Config":
        window = WindowConfig(**_pick(raw.get("window"), WindowConfig))
        assets = AssetConfig(**_pick(raw.get("assets"), AssetConfig))
        platform = PlatformConfig(**_pick(raw.get("platform"), PlatformConfig))
        return cls(
            walk_speed=float(raw.get("walk_speed", cls.walk_speed)),
            idle_time=float(raw.get("idle_time", cls.idle_time)),
            window_scale=float(raw.get("window_scale", cls.window_scale)),
            behavior_enabled=bool(raw.get("behavior_enabled", cls.behavior_enabled)),
            window=window,
            assets=assets,
            platform=platform,
        )


def _pick(section: Any, schema: type) -> dict[str, Any]:
    if not isinstance(section, dict):
        return {}
    allowed = set(schema.__dataclass_fields__)
    return {k: v for k, v in section.items() if k in allowed}
