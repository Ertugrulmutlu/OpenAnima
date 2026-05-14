from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap


DEFAULT_FRAME_DURATION_MS = 100
MAX_APNG_FRAMES = 1000
MAX_TOTAL_PIXELS = 120_000_000


class ApngAnimationPlayer(QObject):
    pixmap_changed = Signal(QPixmap)

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = Path(path)
        self.index = 0
        self.speed = 100
        self.frames: list[tuple[QPixmap, int]] = []
        self.error = ""

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance)
        self.load_frames()

    def load_frames(self):
        try:
            from PIL import Image, ImageSequence
        except ImportError:
            self.error = "Pillow is not installed, so manual APNG playback is unavailable."
            return

        try:
            with Image.open(self.path) as image:
                if not getattr(image, "is_animated", False):
                    self.error = "APNG file did not expose animated frames."
                    return

                total_pixels = 0
                for frame_index, frame in enumerate(ImageSequence.Iterator(image)):
                    if frame_index >= MAX_APNG_FRAMES:
                        self.error = f"APNG has more than {MAX_APNG_FRAMES} frames."
                        self.frames.clear()
                        return

                    rgba = frame.convert("RGBA")
                    total_pixels += rgba.width * rgba.height
                    if total_pixels > MAX_TOTAL_PIXELS:
                        self.error = "APNG is too large to decode safely for overlay playback."
                        self.frames.clear()
                        return

                    duration = _frame_duration_ms(frame)
                    pixmap = _rgba_image_to_pixmap(rgba)
                    if not pixmap.isNull():
                        self.frames.append((pixmap, duration))
        except Exception as exc:
            self.error = f"Could not decode APNG frames with Pillow: {exc}"
            self.frames.clear()

        if len(self.frames) < 2:
            self.error = self.error or "APNG did not contain enough readable frames to animate."
            self.frames.clear()

    def start(self):
        if not self.frames:
            return
        self.index = min(self.index, len(self.frames) - 1)
        self.pixmap_changed.emit(self.frames[self.index][0])
        self.timer.start(self.interval_for_frame(self.index))

    def stop(self):
        self.timer.stop()

    def set_speed(self, multiplier):
        self.speed = max(1, int(multiplier or 100))
        if self.timer.isActive() and self.frames:
            self.timer.setInterval(self.interval_for_frame(self.index))

    def advance(self):
        if not self.frames:
            self.stop()
            return
        self.index = (self.index + 1) % len(self.frames)
        self.pixmap_changed.emit(self.frames[self.index][0])
        self.timer.setInterval(self.interval_for_frame(self.index))

    def interval_for_frame(self, index):
        duration = self.frames[index][1] if self.frames else DEFAULT_FRAME_DURATION_MS
        return max(1, round(duration * 100 / max(1, self.speed)))


def _frame_duration_ms(frame):
    try:
        duration = int(frame.info.get("duration") or DEFAULT_FRAME_DURATION_MS)
    except (TypeError, ValueError):
        duration = DEFAULT_FRAME_DURATION_MS
    return max(1, duration)


def _rgba_image_to_pixmap(image):
    data = image.tobytes("raw", "RGBA")
    qimage = QImage(data, image.width, image.height, image.width * 4, QImage.Format_RGBA8888).copy()
    return QPixmap.fromImage(qimage)
