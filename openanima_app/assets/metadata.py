import json
from pathlib import Path

from ..runtime.logging import log_warning
from .paths import is_supported_frame_file, natural_key


def load_metadata(folder):
    metadata_path = Path(folder) / "asset.json"
    if not metadata_path.exists():
        return {}

    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log_warning("Invalid asset metadata %s: %s", metadata_path, exc)
        return {}

    return data if isinstance(data, dict) else {}


def frame_paths_for_folder(folder):
    return sorted(
        (path for path in Path(folder).iterdir() if path.is_file() and is_supported_frame_file(path)),
        key=natural_key,
    )


def metadata_preview(folder, metadata):
    preview = metadata.get("preview") if isinstance(metadata, dict) else None
    image = metadata.get("image") if isinstance(metadata, dict) else None
    preview_path_value = preview or image
    if not preview_path_value and isinstance(metadata, dict):
        layers = metadata.get("layers")
        if isinstance(layers, list):
            for layer in layers:
                if isinstance(layer, dict) and layer.get("image"):
                    preview_path_value = layer.get("image")
                    break
    if not preview_path_value:
        return None
    preview_path = (Path(folder) / str(preview_path_value)).resolve()
    return preview_path if preview_path.exists() else None


def metadata_int(metadata, key, default):
    try:
        return max(1, int(metadata.get(key, default)))
    except (AttributeError, TypeError, ValueError):
        return default
