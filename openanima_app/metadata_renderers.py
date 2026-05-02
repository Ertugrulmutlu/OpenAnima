from pathlib import Path

from PySide6.QtCore import QObject, QRect, QTimer, Qt, Signal
from PySide6.QtGui import QImage, QPainter, QPixmap

from .logging_utils import log_warning


class SpriteAnimationPlayer(QObject):
    pixmap_changed = Signal(QPixmap)

    def __init__(self, frames, fps=8, loop=True, parent=None):
        super().__init__(parent)
        self.frames = [frame for frame in frames if not frame.isNull()]
        self.fps = max(1, int(fps or 8))
        self.loop = bool(loop)
        self.speed = 100
        self.index = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance)
        self.update_interval()

    def start(self):
        if not self.frames:
            return
        self.index = min(self.index, len(self.frames) - 1)
        self.pixmap_changed.emit(self.frames[self.index])
        if len(self.frames) > 1:
            self.timer.start()

    def stop(self):
        self.timer.stop()

    def set_speed(self, multiplier):
        self.speed = max(1, int(multiplier or 100))
        self.update_interval()

    def update_interval(self):
        interval = round(1000 / self.fps * 100 / max(1, self.speed))
        self.timer.setInterval(max(1, interval))

    def advance(self):
        if not self.frames:
            self.stop()
            return

        next_index = self.index + 1
        if next_index >= len(self.frames):
            if not self.loop:
                self.stop()
                return
            next_index = 0

        self.index = next_index
        self.pixmap_changed.emit(self.frames[self.index])


def load_sprite_strip_frames(asset_folder: Path, metadata: dict) -> list[QPixmap]:
    image_path = _metadata_image_path(asset_folder, metadata)
    if image_path is None:
        log_warning("Sprite strip asset is missing image metadata: %s", asset_folder)
        return []

    sheet = QPixmap(str(image_path))
    if sheet.isNull():
        log_warning("Unable to load sprite strip image: %s", image_path)
        return []

    result = sprite_strip_frames_from_pixmap(sheet, metadata, asset_name=str(asset_folder))
    return result


def sprite_strip_frames_from_pixmap(sheet: QPixmap, metadata: dict, asset_name="sprite_strip") -> list[QPixmap]:
    frames = _positive_int(metadata.get("frames"), 0)
    direction = str(metadata.get("direction") or "horizontal").lower()
    frame_width, frame_height, error = sprite_strip_frame_size(sheet.width(), sheet.height(), metadata)
    if error:
        log_warning("%s", error)
        return []

    crop_left, crop_top, crop_right, crop_bottom = sprite_strip_crop_values(metadata)
    crop_width = frame_width - crop_left - crop_right
    crop_height = frame_height - crop_top - crop_bottom
    if crop_width < 1 or crop_height < 1:
        log_warning(
            "%s",
            sprite_strip_error_message(
                sheet.width(),
                sheet.height(),
                metadata,
                f"crop margins leave an empty frame ({crop_width}x{crop_height})",
            )
        )
        return []

    trim = bool(metadata.get("trim_transparent", False))
    padding = max(0, _int(metadata.get("trim_padding"), 0))
    cropped = []
    for index in range(frames):
        x = index * frame_width if direction == "horizontal" else 0
        y = 0 if direction == "horizontal" else index * frame_height
        cell = sheet.copy(x, y, frame_width, frame_height)
        frame = cell.copy(crop_left, crop_top, crop_width, crop_height)
        if trim:
            frame = _trimmed_on_stable_canvas(frame, padding)
        if not frame.isNull():
            cropped.append(frame)
    return cropped


def sprite_strip_frame_size(image_width: int, image_height: int, metadata: dict) -> tuple[int, int, str | None]:
    frames = _positive_int(metadata.get("frames"), 0)
    if frames < 1:
        return 0, 0, sprite_strip_error_message(image_width, image_height, metadata, "frame count must be greater than zero")

    direction = str(metadata.get("direction") or "horizontal").lower()
    if direction not in {"horizontal", "vertical"}:
        return 0, 0, sprite_strip_error_message(image_width, image_height, metadata, f"direction must be horizontal or vertical, got {direction!r}")

    explicit_width = _int(metadata.get("frame_width"), 0)
    explicit_height = _int(metadata.get("frame_height"), 0)
    if (explicit_width > 0) != (explicit_height > 0):
        return 0, 0, sprite_strip_error_message(
            image_width,
            image_height,
            metadata,
            "frame_width and frame_height must both be provided when using explicit frame size",
        )
    if explicit_width > 0 and explicit_height > 0:
        frame_width, frame_height = explicit_width, explicit_height
        required_width = frame_width * frames if direction == "horizontal" else frame_width
        required_height = frame_height if direction == "horizontal" else frame_height * frames
        if required_width > image_width or required_height > image_height:
            return 0, 0, sprite_strip_error_message(image_width, image_height, metadata, "frame size and frame count exceed image bounds")
        return frame_width, frame_height, None

    if direction == "vertical":
        if image_height % frames != 0:
            return 0, 0, sprite_strip_error_message(
                image_width,
                image_height,
                metadata,
                f"height is not divisible by frames and no frame_height override was provided; computed frame height: {image_height / frames:.2f}",
            )
        return image_width, image_height // frames, None

    if image_width % frames != 0:
        return 0, 0, sprite_strip_error_message(
            image_width,
            image_height,
            metadata,
            f"width is not divisible by frames and no frame_width override was provided; computed frame width: {image_width / frames:.2f}",
        )
    return image_width // frames, image_height, None


def sprite_strip_crop_values(metadata: dict) -> tuple[int, int, int, int]:
    return (
        max(0, _int(metadata.get("crop_left"), 0)),
        max(0, _int(metadata.get("crop_top"), 0)),
        max(0, _int(metadata.get("crop_right"), 0)),
        max(0, _int(metadata.get("crop_bottom"), 0)),
    )


def sprite_strip_error_message(image_width: int, image_height: int, metadata: dict, reason: str) -> str:
    frames = metadata.get("frames")
    direction = metadata.get("direction", "horizontal")
    frame_width = metadata.get("frame_width", "auto")
    frame_height = metadata.get("frame_height", "auto")
    crop_left, crop_top, crop_right, crop_bottom = sprite_strip_crop_values(metadata)
    return (
        "Invalid sprite_strip metadata:\n"
        f"asset: {metadata.get('name') or 'sprite_strip'}\n"
        f"image: {metadata.get('image') or '<missing>'}\n"
        f"image size: {image_width}x{image_height}\n"
        f"frames: {frames}\n"
        f"direction: {direction}\n"
        f"frame_width/frame_height: {frame_width}x{frame_height}\n"
        f"crop: {crop_left}/{crop_top}/{crop_right}/{crop_bottom}\n"
        f"reason: {reason}"
    )


def _trimmed_on_stable_canvas(frame: QPixmap, padding: int) -> QPixmap:
    image = frame.toImage().convertToFormat(QImage.Format_ARGB32)
    bbox = _alpha_bbox(image)
    if bbox is None:
        return QPixmap()

    left, top, right, bottom = bbox
    left = max(0, left - padding)
    top = max(0, top - padding)
    right = min(image.width() - 1, right + padding)
    bottom = min(image.height() - 1, bottom + padding)

    canvas = QPixmap(frame.size())
    canvas.fill(Qt.transparent)
    painter = QPainter(canvas)
    source = QRect(left, top, right - left + 1, bottom - top + 1)
    painter.drawPixmap(source.topLeft(), frame, source)
    painter.end()
    return canvas


def _alpha_bbox(image: QImage):
    left = image.width()
    top = image.height()
    right = -1
    bottom = -1
    for y in range(image.height()):
        for x in range(image.width()):
            if image.pixelColor(x, y).alpha() > 0:
                left = min(left, x)
                top = min(top, y)
                right = max(right, x)
                bottom = max(bottom, y)
    if right < 0:
        return None
    return left, top, right, bottom


def load_spritesheet_frames(asset_folder: Path, metadata: dict, animation_name=None) -> tuple[list[QPixmap], int, bool, str | None]:
    image_path = _metadata_image_path(asset_folder, metadata)
    if image_path is None:
        log_warning("Spritesheet asset is missing image metadata: %s", asset_folder)
        return [], _metadata_fps(metadata, None), True, None

    sheet = QPixmap(str(image_path))
    if sheet.isNull():
        log_warning("Unable to load spritesheet image: %s", image_path)
        return [], _metadata_fps(metadata, None), True, None

    frame_width = _positive_int(metadata.get("frame_width"), 0)
    frame_height = _positive_int(metadata.get("frame_height"), 0)
    if frame_width < 1 or frame_height < 1:
        log_warning("Spritesheet asset has invalid frame dimensions: %s", asset_folder)
        return [], _metadata_fps(metadata, None), True, None

    selected_name, animation = _selected_animation(metadata, animation_name)
    frame_specs = animation.get("frames") if isinstance(animation, dict) else None
    if not isinstance(frame_specs, list) or not frame_specs:
        frame_specs = [{"x": 0, "y": 0}]

    frames = []
    for frame_spec in frame_specs:
        rect = _frame_rect(frame_spec, frame_width, frame_height)
        if rect is None:
            continue
        if rect.right() >= sheet.width() or rect.bottom() >= sheet.height():
            log_warning("Spritesheet frame outside image bounds skipped: %s %s", image_path, rect)
            continue
        frame = sheet.copy(rect)
        if not frame.isNull():
            frames.append(frame)

    fps = _metadata_fps(animation, _metadata_fps(metadata, 8))
    loop = bool(animation.get("loop", metadata.get("loop", True))) if isinstance(animation, dict) else bool(metadata.get("loop", True))
    return frames, fps, loop, selected_name


class CompositeUIRenderer:
    def __init__(self, asset_folder: Path, metadata: dict):
        self.asset_folder = Path(asset_folder)
        self.metadata = metadata or {}
        self.layers = []
        self.size = None
        self.load_layers()

    def load_layers(self):
        max_width = 1
        max_height = 1
        for layer in self.metadata.get("layers", []):
            if not isinstance(layer, dict):
                continue
            image_name = layer.get("image")
            if not image_name:
                log_warning("Composite UI layer is missing image metadata: %s", self.asset_folder)
                continue
            image_path = (self.asset_folder / str(image_name)).resolve()
            pixmap = QPixmap(str(image_path))
            if pixmap.isNull():
                log_warning("Composite UI layer image skipped: %s", image_path)
                continue
            x = _int(layer.get("x"), 0)
            y = _int(layer.get("y"), 0)
            max_width = max(max_width, x + pixmap.width())
            max_height = max(max_height, y + pixmap.height())
            self.layers.append({"metadata": dict(layer), "pixmap": pixmap, "x": x, "y": y})

        width = _positive_int(self.metadata.get("width"), max_width)
        height = _positive_int(self.metadata.get("height"), max_height)
        self.size = (width, height)

    def set_layer_value(self, name, value):
        for layer in self.layers:
            if layer["metadata"].get("name") == name:
                layer["metadata"]["value"] = _clamp_float(value)
        return self.render()

    def render(self) -> QPixmap:
        width, height = self.size or (1, 1)
        canvas = QPixmap(width, height)
        canvas.fill(Qt.transparent)

        painter = QPainter(canvas)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        for layer in self.layers:
            self._draw_layer(painter, layer)
        painter.end()
        return canvas

    def _draw_layer(self, painter: QPainter, layer: dict):
        pixmap = layer["pixmap"]
        metadata = layer["metadata"]
        if metadata.get("visible", True) is False:
            return

        x = layer["x"]
        y = layer["y"]
        clip = str(metadata.get("clip") or "").lower()
        opacity = _clamp_float(metadata.get("opacity", 1.0))
        old_opacity = painter.opacity()
        painter.setOpacity(old_opacity * opacity)

        if clip == "horizontal":
            value = _clamp_float(metadata.get("value", 1.0))
            width = max(0, round(pixmap.width() * value))
            if width:
                source = QRect(0, 0, width, pixmap.height())
                target = QRect(x, y, width, pixmap.height())
                painter.drawPixmap(target, pixmap, source)
            painter.setOpacity(old_opacity)
            return

        if clip == "vertical":
            value = _clamp_float(metadata.get("value", 1.0))
            height = max(0, round(pixmap.height() * value))
            if height:
                source = QRect(0, 0, pixmap.width(), height)
                target = QRect(x, y, pixmap.width(), height)
                painter.drawPixmap(target, pixmap, source)
            painter.setOpacity(old_opacity)
            return

        painter.drawPixmap(x, y, pixmap)
        painter.setOpacity(old_opacity)


def _metadata_image_path(asset_folder: Path, metadata: dict) -> Path | None:
    image_name = metadata.get("image") if isinstance(metadata, dict) else None
    if not image_name:
        return None
    return (Path(asset_folder) / str(image_name)).resolve()


def _selected_animation(metadata: dict, animation_name=None) -> tuple[str | None, dict]:
    animations = metadata.get("animations")
    if not isinstance(animations, dict) or not animations:
        return None, {}

    if animation_name in animations and isinstance(animations[animation_name], dict):
        return str(animation_name), animations[animation_name]

    default_animation = metadata.get("default_animation")
    if default_animation in animations and isinstance(animations[default_animation], dict):
        return str(default_animation), animations[default_animation]

    for name, animation in animations.items():
        if isinstance(animation, dict):
            return str(name), animation
    return None, {}


def _frame_rect(frame_spec, frame_width: int, frame_height: int) -> QRect | None:
    if not isinstance(frame_spec, dict):
        return None

    if "col" in frame_spec or "row" in frame_spec:
        col = _int(frame_spec.get("col"), 0)
        row = _int(frame_spec.get("row"), 0)
        return QRect(col * frame_width, row * frame_height, frame_width, frame_height)

    x = _int(frame_spec.get("x"), 0)
    y = _int(frame_spec.get("y"), 0)
    return QRect(x, y, frame_width, frame_height)


def _metadata_fps(metadata, default):
    if not isinstance(metadata, dict):
        return default if default is not None else 8
    return _positive_int(metadata.get("fps"), default if default is not None else 8)


def _positive_int(value, default):
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


def _int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp_float(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 1.0
    return min(1.0, max(0.0, number))
