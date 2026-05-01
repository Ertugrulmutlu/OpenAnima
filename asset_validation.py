from pathlib import Path

from PySide6.QtGui import QPixmap

from .assets import AssetType


def validate_asset_metadata(asset_definition) -> list[str]:
    asset_type = getattr(asset_definition, "type", None)
    folder = Path(getattr(asset_definition, "path", ""))
    metadata = getattr(asset_definition, "metadata", None) or {}

    if asset_type == AssetType.SPRITE_STRIP:
        return _validate_sprite_strip(folder, metadata)
    if asset_type == AssetType.SPRITESHEET:
        return _validate_spritesheet(folder, metadata)
    if asset_type == AssetType.COMPOSITE_UI:
        return _validate_composite_ui(folder, metadata)
    return []


def _validate_sprite_strip(folder: Path, metadata: dict) -> list[str]:
    errors = []
    image_path = _image_path(folder, metadata)
    pixmap = _pixmap(image_path)
    if image_path is None or not image_path.exists():
        errors.append("Sprite strip image file is missing.")
        return errors
    if pixmap.isNull():
        errors.append("Sprite strip image file is not readable.")
        return errors

    frames = _int(metadata.get("frames"), 0)
    if frames <= 0:
        errors.append("Sprite strip frame count must be greater than zero.")
        return errors

    direction = str(metadata.get("direction") or "horizontal").lower()
    if direction not in {"horizontal", "vertical"}:
        errors.append("Sprite strip direction must be horizontal or vertical.")
        return errors

    frame_width = _int(metadata.get("frame_width"), 0)
    frame_height = _int(metadata.get("frame_height"), 0)
    if frame_width > 0 or frame_height > 0:
        if frame_width <= 0 or frame_height <= 0:
            errors.append("Sprite strip frame_width and frame_height must both be greater than zero when provided.")
            return errors
        required_width = frame_width * frames if direction == "horizontal" else frame_width
        required_height = frame_height if direction == "horizontal" else frame_height * frames
        if required_width > pixmap.width() or required_height > pixmap.height():
            errors.append("Sprite strip frame size and frame count exceed the image bounds.")
        _validate_sprite_strip_crop(metadata, frame_width, frame_height, errors)
        return errors

    dimension = pixmap.width() if direction == "horizontal" else pixmap.height()
    if dimension % frames != 0:
        errors.append(f"Sprite strip {direction} dimension {dimension}px is not divisible by {frames} frames and no frame size override was provided.")
        return errors

    frame_width = pixmap.width() if direction == "vertical" else pixmap.width() // frames
    frame_height = pixmap.height() if direction == "horizontal" else pixmap.height() // frames
    _validate_sprite_strip_crop(metadata, frame_width, frame_height, errors)
    return errors


def _validate_sprite_strip_crop(metadata: dict, frame_width: int, frame_height: int, errors: list[str]):
    crop_left = _int(metadata.get("crop_left"), 0)
    crop_top = _int(metadata.get("crop_top"), 0)
    crop_right = _int(metadata.get("crop_right"), 0)
    crop_bottom = _int(metadata.get("crop_bottom"), 0)
    crops = {
        "crop_left": crop_left,
        "crop_top": crop_top,
        "crop_right": crop_right,
        "crop_bottom": crop_bottom,
    }
    for name, value in crops.items():
        if value < 0:
            errors.append(f"Sprite strip {name} must be zero or greater.")
    if crop_left + crop_right >= frame_width:
        errors.append("Sprite strip crop_left + crop_right must be smaller than frame_width.")
    if crop_top + crop_bottom >= frame_height:
        errors.append("Sprite strip crop_top + crop_bottom must be smaller than frame_height.")


def _validate_spritesheet(folder: Path, metadata: dict) -> list[str]:
    errors = []
    image_path = _image_path(folder, metadata)
    pixmap = _pixmap(image_path)
    if image_path is None or not image_path.exists():
        errors.append("Spritesheet image file is missing.")
        return errors
    if pixmap.isNull():
        errors.append("Spritesheet image file is not readable.")
        return errors

    frame_width = _int(metadata.get("frame_width"), 0)
    frame_height = _int(metadata.get("frame_height"), 0)
    if frame_width <= 0 or frame_height <= 0:
        errors.append("Spritesheet frame_width and frame_height must be greater than zero.")

    animations = metadata.get("animations")
    if not isinstance(animations, dict) or not animations:
        errors.append("Spritesheet must define at least one animation.")
        return errors

    for name, animation in animations.items():
        frames = animation.get("frames") if isinstance(animation, dict) else None
        if not isinstance(frames, list) or not frames:
            errors.append(f"Spritesheet animation '{name}' must define at least one frame.")
            continue
        for index, frame in enumerate(frames):
            if not isinstance(frame, dict) or not (("col" in frame and "row" in frame) or ("x" in frame and "y" in frame)):
                errors.append(f"Spritesheet animation '{name}' frame {index + 1} needs col/row or x/y.")
    return errors


def _validate_composite_ui(folder: Path, metadata: dict) -> list[str]:
    errors = []
    layers = metadata.get("layers")
    if not isinstance(layers, list) or not layers:
        return ["Composite UI assets need at least one layer."]

    readable = 0
    for index, layer in enumerate(layers):
        if not isinstance(layer, dict):
            errors.append(f"Composite UI layer {index + 1} is invalid.")
            continue
        image = layer.get("image")
        if not image:
            errors.append(f"Composite UI layer {index + 1} is missing an image.")
            continue
        image_path = folder / str(image)
        if not image_path.exists():
            errors.append(f"Composite UI layer image is missing: {image}")
            continue
        if _pixmap(image_path).isNull():
            errors.append(f"Composite UI layer image is not readable: {image}")
            continue
        readable += 1

    if readable == 0:
        errors.append("Composite UI assets need at least one readable layer.")
    return errors


def _image_path(folder: Path, metadata: dict) -> Path | None:
    image = metadata.get("image")
    if not image:
        return None
    if folder.is_file():
        return folder if folder.name == str(image) else folder.parent / str(image)
    return folder / str(image)


def _pixmap(path: Path | None) -> QPixmap:
    return QPixmap(str(path)) if path is not None else QPixmap()


def _int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
