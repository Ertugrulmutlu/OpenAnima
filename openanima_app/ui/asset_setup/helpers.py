from pathlib import Path

from PySide6.QtGui import QPixmap

from ...assets.constants import SUPPORTED_IMAGE_EXTENSIONS
from ...assets.paths import is_supported_frame_file, natural_key


PREVIEW_TERMS = ("preview", "sample", "example")
BASE_TERMS = ("hp bar", "base", "frame", "background", "bg")
HEALTH_TERMS = ("red", "health", "hp")
ENERGY_TERMS = ("blue", "mana", "mp", "energy")
STAMINA_TERMS = ("yellow", "stamina", "xp")


def image_files(path: Path):
    path = Path(path)
    if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS:
        return [path]
    if not path.is_dir():
        return []
    return sorted((item for item in path.iterdir() if item.is_file() and is_supported_frame_file(item)), key=natural_key)


def default_name(path: Path):
    return path.stem if path.is_file() else path.name


def default_layer_for_image(path: Path):
    stem = path.stem.lower()
    if matches(path, BASE_TERMS):
        return {"name": "base", "image": path.name, "x": 0, "y": 0, "visible": True, "opacity": 1.0, "clip": "none", "value": 1.0, "role": "base"}
    if any(term in stem for term in HEALTH_TERMS):
        return {"name": "health", "image": path.name, "x": 0, "y": 0, "visible": True, "opacity": 1.0, "clip": "horizontal", "value": 1.0, "role": "health"}
    if any(term in stem for term in ENERGY_TERMS):
        return {"name": "energy", "image": path.name, "x": 0, "y": 0, "visible": True, "opacity": 1.0, "clip": "horizontal", "value": 1.0, "role": "mana"}
    if any(term in stem for term in STAMINA_TERMS):
        return {"name": "stamina", "image": path.name, "x": 0, "y": 0, "visible": True, "opacity": 1.0, "clip": "horizontal", "value": 1.0, "role": "stamina"}
    return {"name": path.stem, "image": path.name, "x": 0, "y": 0, "visible": True, "opacity": 1.0, "clip": "none", "value": 1.0, "role": "normal"}


def normalized_layer(layer):
    normalized = default_layer_for_image(Path(str(layer.get("image") or "layer.png")))
    normalized.update(layer)
    normalized.setdefault("visible", True)
    normalized.setdefault("opacity", 1.0)
    normalized.setdefault("clip", "none")
    normalized.setdefault("value", 1.0)
    normalized.setdefault("role", "normal")
    return normalized


def matches(path: Path, terms):
    stem = path.stem.lower()
    return any(term in stem for term in terms)


def readable_image(folder: Path, image_name: str):
    folder = Path(folder)
    image_path = folder / image_name if folder.is_dir() else folder
    pixmap = QPixmap(str(image_path))
    return not pixmap.isNull()


def int_value(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def float_value(value, default):
    try:
        return min(1.0, max(0.0, float(value)))
    except (TypeError, ValueError):
        return default
