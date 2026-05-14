import re
from pathlib import Path

from ..runtime import state
from ..runtime.paths import BASE_DIR
from .constants import SUPPORTED_ASSET_EXTENSIONS, SUPPORTED_IMAGE_EXTENSIONS


def stored_path(path):
    path = Path(path).resolve()
    try:
        return path.relative_to(BASE_DIR).as_posix()
    except ValueError:
        return str(path)


def resolved_path(path):
    path = Path(path).expanduser()
    return path if path.is_absolute() else BASE_DIR / path


def resolve_saved_asset_path(path, asset_root=None):
    raw_path = Path(str(path or "")).expanduser()
    if raw_path.is_absolute():
        return raw_path

    roots = []
    if asset_root is not None:
        roots.append(Path(asset_root))
    roots.extend([state.ASSETS_DIR, BASE_DIR, Path.cwd()])

    seen = set()
    fallback = None
    for root in roots:
        candidate = (Path(root).expanduser() / raw_path).resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        fallback = fallback or candidate
        if candidate.exists():
            return candidate

    return fallback or (BASE_DIR / raw_path).resolve()


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
