import shutil
from pathlib import Path

from ..runtime import state
from ..runtime.logging import log_warning
from ..runtime.paths import BUNDLED_ASSETS_DIR, DEFAULT_ASSETS_DIR
from .detection import detect_asset
from .paths import is_inside_assets, is_supported_asset_file, unique_asset_path, unique_folder_path


def ensure_assets_dir():
    try:
        state.ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        log_warning("Could not create runtime assets folder %s: %s", state.ASSETS_DIR, exc)
        return False
    return True


def seed_default_assets_dir():
    if state.ASSETS_DIR != DEFAULT_ASSETS_DIR:
        return
    if BUNDLED_ASSETS_DIR.resolve() == DEFAULT_ASSETS_DIR.resolve():
        return
    if not BUNDLED_ASSETS_DIR.exists():
        return
    if DEFAULT_ASSETS_DIR.exists() and any(DEFAULT_ASSETS_DIR.iterdir()):
        return

    try:
        shutil.copytree(BUNDLED_ASSETS_DIR, DEFAULT_ASSETS_DIR, dirs_exist_ok=True)
    except OSError as exc:
        log_warning("Could not seed bundled assets into runtime assets folder: %s", exc)


def import_asset_to_assets(source, pack_dir=None, reuse_existing=False):
    source = Path(source).resolve()
    if not source.exists() or not source.is_file() or not is_supported_asset_file(source):
        log_warning("Unsupported asset import skipped: %s", source)
        return None

    if not ensure_assets_dir():
        return None
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
        log_warning("Unsupported asset folder import skipped: %s", source)
        return None

    if not ensure_assets_dir():
        return None
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
