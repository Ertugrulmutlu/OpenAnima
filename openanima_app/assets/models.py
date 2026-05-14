from dataclasses import dataclass
from pathlib import Path


class AssetType:
    GIF = "gif"
    APNG = "apng"
    WEBM = "webm"
    STATIC_IMAGE = "static_image"
    FRAME_ANIMATION = "frame_animation"
    SPRITE_STRIP = "sprite_strip"
    SPRITESHEET = "spritesheet"
    COMPOSITE_UI = "composite_ui"
    UNKNOWN = "unknown"


@dataclass
class AssetDefinition:
    id: str
    name: str
    type: str
    path: Path
    pack: str | None = None
    metadata: dict | None = None
    preview_path: Path | None = None
    fps: int | None = None
