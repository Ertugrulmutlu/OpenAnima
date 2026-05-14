from pathlib import Path

from ..runtime import state
from .constants import DEFAULT_FRAME_FPS, METADATA_ASSET_TYPES, SUPPORTED_IMAGE_EXTENSIONS
from .metadata import frame_paths_for_folder, load_metadata, metadata_int, metadata_preview
from .models import AssetDefinition, AssetType
from .paths import stored_path


def pack_name_for(path):
    try:
        relative = Path(path).resolve().relative_to(state.ASSETS_DIR.resolve())
    except ValueError:
        return None
    return relative.parts[0] if len(relative.parts) > 1 else None


_metadata_preview = metadata_preview
_metadata_int = metadata_int


def detect_asset(path):
    path = Path(path).resolve()
    if path.is_file():
        suffix = path.suffix.lower()
        if suffix == ".gif":
            asset_type = AssetType.GIF
        elif suffix == ".apng" or is_apng_file(path):
            asset_type = AssetType.APNG
        elif suffix == ".webm":
            asset_type = AssetType.WEBM
        elif suffix in SUPPORTED_IMAGE_EXTENSIONS:
            asset_type = AssetType.STATIC_IMAGE
        else:
            return None

        return AssetDefinition(
            id=stored_path(path),
            name=path.stem,
            type=asset_type,
            path=path,
            pack=pack_name_for(path),
            metadata={},
            preview_path=path,
        )

    if path.is_dir():
        metadata = load_metadata(path)
        metadata_type = str(metadata.get("type") or "").strip().lower() if metadata else ""
        if metadata_type in METADATA_ASSET_TYPES and metadata_type != AssetType.FRAME_ANIMATION:
            return AssetDefinition(
                id=stored_path(path),
                name=str(metadata.get("name") or path.name),
                type=metadata_type,
                path=path,
                pack=pack_name_for(path),
                metadata=metadata,
                preview_path=metadata_preview(path, metadata),
                fps=metadata_int(metadata, "fps", DEFAULT_FRAME_FPS),
            )

        frames = frame_paths_for_folder(path)
        if len(frames) < 2:
            return None

        fps = metadata_int(metadata, "fps", DEFAULT_FRAME_FPS)

        return AssetDefinition(
            id=stored_path(path),
            name=str(metadata.get("name") or path.name),
            type=metadata_type if metadata_type == AssetType.FRAME_ANIMATION else AssetType.FRAME_ANIMATION,
            path=path,
            pack=pack_name_for(path),
            metadata=metadata,
            preview_path=metadata_preview(path, metadata) or frames[0],
            fps=fps,
        )

    return None


def is_apng_file(path):
    path = Path(path)
    if path.suffix.lower() not in {".png", ".apng"}:
        return False
    try:
        with path.open("rb") as file:
            if file.read(8) != b"\x89PNG\r\n\x1a\n":
                return False
            while True:
                length_bytes = file.read(4)
                if len(length_bytes) != 4:
                    return False
                length = int.from_bytes(length_bytes, "big")
                chunk_type = file.read(4)
                if len(chunk_type) != 4:
                    return False
                if chunk_type == b"acTL":
                    return True
                if chunk_type in {b"IDAT", b"IEND"}:
                    return False
                file.seek(length + 4, 1)
    except OSError:
        return False
