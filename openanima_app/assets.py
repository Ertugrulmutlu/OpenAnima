import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QImageReader, QMovie, QPixmap

from .constants import BASE_DIR, CONFIG_PATH, DEFAULT_ASSETS_DIR, THUMBNAIL_SIZE
from . import state


class AssetType:
    GIF = "gif"
    STATIC_IMAGE = "static_image"
    FRAME_ANIMATION = "frame_animation"
    SPRITE_STRIP = "sprite_strip"
    SPRITESHEET = "spritesheet"
    COMPOSITE_UI = "composite_ui"
    UNKNOWN = "unknown"


SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
SUPPORTED_ASSET_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS | {".gif"}
DEFAULT_FRAME_FPS = 12
METADATA_ASSET_TYPES = {
    AssetType.FRAME_ANIMATION,
    AssetType.SPRITE_STRIP,
    AssetType.SPRITESHEET,
    AssetType.COMPOSITE_UI,
}
CONFIG_SCHEMA_VERSION = 1
WINDOW_CONFIG_KEYS = {
    "path",
    "gif_path",
    "asset_path",
    "asset_id",
    "asset_type",
    "x",
    "y",
    "locked",
    "always_on_top",
    "click_through",
    "scale",
    "opacity",
    "speed",
    "layer_values",
    "current_animation",
}


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


def ensure_assets_dir():
    state.ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def stored_path(path):
    path = Path(path).resolve()
    try:
        return path.relative_to(BASE_DIR).as_posix()
    except ValueError:
        return str(path)


def resolved_path(path):
    path = Path(path)
    return path if path.is_absolute() else BASE_DIR / path


def config_warning(message):
    state.CONFIG_WARNINGS.append(message)
    print(f"Warning: {message}")


def is_inside_assets(path):
    try:
        Path(path).resolve().relative_to(state.ASSETS_DIR.resolve())
        return True
    except ValueError:
        return False


def unique_asset_path(target_dir, filename):
    target_dir.mkdir(parents=True, exist_ok=True)
    base = Path(filename).stem
    suffix = Path(filename).suffix or ".gif"
    candidate = target_dir / f"{base}{suffix}"
    index = 1

    while candidate.exists():
        candidate = target_dir / f"{base}_{index}{suffix}"
        index += 1

    return candidate


def unique_folder_path(target_dir, folder_name):
    target_dir.mkdir(parents=True, exist_ok=True)
    base = Path(folder_name).name
    candidate = target_dir / base
    index = 1

    while candidate.exists():
        candidate = target_dir / f"{base}_{index}"
        index += 1

    return candidate


def natural_key(path):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", Path(path).name)]


def is_supported_asset_file(path):
    return Path(path).suffix.lower() in SUPPORTED_ASSET_EXTENSIONS


def is_supported_frame_file(path):
    return Path(path).suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS


def load_metadata(folder):
    metadata_path = Path(folder) / "asset.json"
    if not metadata_path.exists():
        return {}

    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Warning: invalid asset metadata {metadata_path}: {exc}")
        return {}

    return data if isinstance(data, dict) else {}


def frame_paths_for_folder(folder):
    return sorted(
        (path for path in Path(folder).iterdir() if path.is_file() and is_supported_frame_file(path)),
        key=natural_key,
    )


def pack_name_for(path):
    try:
        relative = Path(path).resolve().relative_to(state.ASSETS_DIR.resolve())
    except ValueError:
        return None
    return relative.parts[0] if len(relative.parts) > 1 else None


def _metadata_preview(folder, metadata):
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


def _metadata_int(metadata, key, default):
    try:
        return max(1, int(metadata.get(key, default)))
    except (AttributeError, TypeError, ValueError):
        return default


def detect_asset(path):
    path = Path(path).resolve()
    if path.is_file():
        suffix = path.suffix.lower()
        if suffix == ".gif":
            asset_type = AssetType.GIF
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
                preview_path=_metadata_preview(path, metadata),
                fps=_metadata_int(metadata, "fps", DEFAULT_FRAME_FPS),
            )

        frames = frame_paths_for_folder(path)
        if len(frames) < 2:
            return None

        fps = _metadata_int(metadata, "fps", DEFAULT_FRAME_FPS)

        return AssetDefinition(
            id=stored_path(path),
            name=str(metadata.get("name") or path.name),
            type=metadata_type if metadata_type == AssetType.FRAME_ANIMATION else AssetType.FRAME_ANIMATION,
            path=path,
            pack=pack_name_for(path),
            metadata=metadata,
            preview_path=_metadata_preview(path, metadata) or frames[0],
            fps=fps,
        )

    return None


def scan_assets(root_dir):
    root = Path(root_dir)
    if not root.exists():
        return []

    assets = []
    seen = set()

    def visit(folder):
        for path in sorted(folder.iterdir(), key=lambda item: item.name.lower()):
            if path.name == "asset.json":
                continue
            if path.is_file() and is_supported_asset_file(path):
                asset = detect_asset(path)
                if asset is not None and asset.id not in seen:
                    assets.append(asset)
                    seen.add(asset.id)
            elif path.is_dir():
                asset = detect_asset(path)
                if asset is not None:
                    if asset.id not in seen:
                        assets.append(asset)
                        seen.add(asset.id)
                    continue
                visit(path)

    visit(root)

    return assets


def assets_for_pack(pack_dir):
    ensure_assets_dir()
    pack_dir = Path(pack_dir).resolve()
    assets = []
    seen = set()

    for path in sorted(pack_dir.iterdir(), key=lambda item: item.name.lower()):
        if path.is_file() and is_supported_asset_file(path):
            asset = detect_asset(path)
            if asset is not None and asset.id not in seen:
                assets.append(asset)
                seen.add(asset.id)
        elif path.is_dir():
            asset = detect_asset(path)
            if asset is not None and asset.id not in seen:
                assets.append(asset)
                seen.add(asset.id)
                continue

            for nested in scan_assets(path):
                if nested.id not in seen:
                    assets.append(nested)
                    seen.add(nested.id)

    return assets


def import_asset_to_assets(source, pack_dir=None, reuse_existing=False):
    source = Path(source).resolve()
    if not source.exists() or not source.is_file() or not is_supported_asset_file(source):
        return None

    ensure_assets_dir()
    if is_inside_assets(source):
        return source

    target_dir = Path(pack_dir).resolve() if pack_dir else state.ASSETS_DIR
    existing_target = target_dir / source.name
    if reuse_existing and existing_target.exists():
        return existing_target

    target = unique_asset_path(target_dir, source.name)
    shutil.copy2(source, target)
    return target


def import_folder_to_assets(source, pack_dir=None, reuse_existing=False):
    source = Path(source).resolve()
    if not source.exists() or not source.is_dir() or detect_asset(source) is None:
        return None

    ensure_assets_dir()
    if is_inside_assets(source):
        return source

    target_dir = Path(pack_dir).resolve() if pack_dir else state.ASSETS_DIR
    existing_target = target_dir / source.name
    if reuse_existing and existing_target.exists():
        return existing_target

    target = unique_folder_path(target_dir, source.name)
    shutil.copytree(source, target)
    return target


def import_gif_to_assets(source, pack_dir=None, reuse_existing=False):
    source = Path(source).resolve()
    if source.suffix.lower() != ".gif":
        return None
    return import_asset_to_assets(source, pack_dir, reuse_existing)


def asset_packs():
    ensure_assets_dir()
    packs = [("Root assets", state.ASSETS_DIR)]
    packs.extend((path.name, path) for path in sorted(state.ASSETS_DIR.iterdir()) if path.is_dir())
    return packs


def gifs_for_pack(pack_dir):
    pack_dir = Path(pack_dir)
    if pack_dir == state.ASSETS_DIR:
        return sorted(path for path in state.ASSETS_DIR.glob("*.gif") if path.is_file())
    return sorted(path for path in pack_dir.glob("*.gif") if path.is_file())


def make_thumbnail(asset_or_path):
    path = asset_or_path.preview_path if isinstance(asset_or_path, AssetDefinition) else asset_or_path
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    image = reader.read()

    if image.isNull():
        movie = QMovie(str(path))
        movie.start()
        pixmap = movie.currentPixmap()
        movie.stop()
    else:
        pixmap = QPixmap.fromImage(image)

    if pixmap.isNull():
        pixmap = QPixmap(THUMBNAIL_SIZE)
        pixmap.fill(Qt.transparent)

    return QIcon(pixmap.scaled(THUMBNAIL_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation))


def default_config():
    return {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "asset_root": stored_path(DEFAULT_ASSETS_DIR),
        "windows": [],
    }


def corrupt_config_backup_path(config_path):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return config_path.with_name(f"{config_path.stem}.corrupt.{timestamp}{config_path.suffix}")


def backup_corrupt_config(config_path):
    backup_path = corrupt_config_backup_path(config_path)
    try:
        shutil.copy2(config_path, backup_path)
        config_warning(f"Invalid config backed up to {backup_path}")
    except OSError as exc:
        config_warning(f"Invalid config could not be backed up: {exc}")
    return backup_path


def normalize_window_config(item):
    if isinstance(item, str):
        return {"path": item} if item else None

    if not isinstance(item, dict):
        config_warning("Skipped saved overlay with invalid entry type.")
        return None

    path_value = item.get("path") or item.get("gif_path") or item.get("asset_path")
    if not isinstance(path_value, str) or not path_value.strip():
        config_warning("Skipped saved overlay without a valid asset path.")
        return None

    normalized = {key: value for key, value in item.items() if key in WINDOW_CONFIG_KEYS}
    normalized["path"] = path_value
    return normalized


def normalize_config_data(data):
    if isinstance(data, list):
        raw_windows = data
        asset_root = None
    elif isinstance(data, dict):
        schema_version = data.get("schema_version", 0)
        if schema_version not in (0, CONFIG_SCHEMA_VERSION):
            config_warning(f"Config schema version {schema_version} is newer than supported; attempting safe load.")

        asset_root = data.get("asset_root")
        raw_windows = data.get("windows", [])
        if not isinstance(raw_windows, list):
            config_warning("Config windows field was invalid; starting with no saved overlays.")
            raw_windows = []
    else:
        config_warning("Config root was invalid; starting with safe defaults.")
        asset_root = None
        raw_windows = []

    if isinstance(asset_root, str) and asset_root.strip():
        state.ASSETS_DIR = resolved_path(asset_root).expanduser().resolve()
    else:
        state.ASSETS_DIR = DEFAULT_ASSETS_DIR

    windows = []
    for item in raw_windows:
        normalized = normalize_window_config(item)
        if normalized is not None:
            windows.append(normalized)

    return {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "asset_root": stored_path(state.ASSETS_DIR),
        "windows": windows,
    }


def load_config_data(config_path=CONFIG_PATH):
    config_path = Path(config_path)
    if not config_path.exists():
        state.ASSETS_DIR = DEFAULT_ASSETS_DIR
        return default_config()

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        backup_corrupt_config(config_path)
        state.ASSETS_DIR = DEFAULT_ASSETS_DIR
        return default_config()
    except OSError as exc:
        config_warning(f"Could not read config: {exc}")
        state.ASSETS_DIR = DEFAULT_ASSETS_DIR
        return default_config()

    return normalize_config_data(data)


def atomic_write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    content = json.dumps(data, indent=2)

    with temp_path.open("w", encoding="utf-8") as file:
        file.write(content)
        file.write("\n")
        file.flush()
        os.fsync(file.fileno())

    os.replace(temp_path, path)


def load_config():
    return load_config_data(CONFIG_PATH)["windows"]


def save_config(windows=None):
    windows = state.WINDOWS if windows is None else windows
    data = {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "asset_root": stored_path(state.ASSETS_DIR),
        "windows": [window.to_config() for window in windows],
    }
    atomic_write_json(CONFIG_PATH, data)
