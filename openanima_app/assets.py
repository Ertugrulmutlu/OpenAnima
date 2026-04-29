import json
import shutil
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QImageReader, QMovie, QPixmap

from .constants import BASE_DIR, CONFIG_PATH, DEFAULT_ASSETS_DIR, THUMBNAIL_SIZE
from . import state


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


def import_gif_to_assets(source, pack_dir=None, reuse_existing=False):
    source = Path(source).resolve()
    if not source.exists() or source.suffix.lower() != ".gif":
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


def make_thumbnail(path):
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
