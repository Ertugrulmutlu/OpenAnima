import json
import re
import shutil
from dataclasses import dataclass
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


def load_config():
    if not CONFIG_PATH.exists():
        state.ASSETS_DIR = DEFAULT_ASSETS_DIR
        return []

    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    if isinstance(data, dict):
        asset_root = data.get("asset_root")
        state.ASSETS_DIR = resolved_path(asset_root).expanduser().resolve() if asset_root else DEFAULT_ASSETS_DIR
        windows = data.get("windows", [])
        return windows if isinstance(windows, list) else []

    state.ASSETS_DIR = DEFAULT_ASSETS_DIR
    return data if isinstance(data, list) else []


def save_config(windows=None):
    windows = state.WINDOWS if windows is None else windows
    data = {
        "asset_root": stored_path(state.ASSETS_DIR),
        "windows": [window.to_config() for window in windows],
    }
    CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
