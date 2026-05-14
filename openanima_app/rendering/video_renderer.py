from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtMultimedia import QMediaPlayer, QVideoSink

from ..runtime.logging import log_warning
from .webm import webm_likely_has_alpha


DEFAULT_VIDEO_SIZE = (320, 180)


class VideoAssetRenderer(QObject):
    pixmap_changed = Signal(QPixmap)
    size_changed = Signal(int, int)
    error_changed = Signal(str)
    warning_changed = Signal(str)

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = Path(path)
        self.error = ""
        self.first_frame_received = False
        self.likely_has_alpha = webm_likely_has_alpha(self.path)
        self.alpha_checked = False
        self.alpha_supported = False

        self.sink = QVideoSink(self)
        self.player = QMediaPlayer(self)
        self.player.setVideoSink(self.sink)
        self.player.setLoops(QMediaPlayer.Loops.Infinite)
        self.sink.videoFrameChanged.connect(self.handle_frame)
        self.player.errorOccurred.connect(self.handle_error)
        self.player.setSource(QUrl.fromLocalFile(str(self.path)))

    def start(self):
        self.player.play()

    def stop(self):
        self.player.stop()

    def release(self):
        self.player.stop()
        self.player.setSource(QUrl())

    def set_speed(self, multiplier):
        try:
            self.player.setPlaybackRate(max(0.01, int(multiplier or 100) / 100))
        except (TypeError, ValueError):
            self.player.setPlaybackRate(1.0)

    def placeholder_pixmap(self):
        pixmap = QPixmap(*DEFAULT_VIDEO_SIZE)
        pixmap.fill()
        return pixmap

    def handle_frame(self, frame):
        if not frame.isValid():
            return

        image = frame.toImage()
        if image.isNull():
            return

        self.check_alpha_support(image)
        # Keep alpha if the Qt multimedia backend exposes it; otherwise this is opaque video.
        image = image.convertToFormat(QImage.Format_ARGB32)
        pixmap = QPixmap.fromImage(image)
        if pixmap.isNull():
            return

        if not self.first_frame_received:
            self.first_frame_received = True
            self.size_changed.emit(pixmap.width(), pixmap.height())
        self.pixmap_changed.emit(pixmap)

    def check_alpha_support(self, image):
        if self.alpha_checked:
            return
        self.alpha_checked = True
        self.alpha_supported = bool(image.hasAlphaChannel())
        if self.likely_has_alpha:
            message = "Transparent WebM alpha may not be preserved by your current Qt video backend."
            log_warning("%s", message)
            self.warning_changed.emit(message)

    def handle_error(self, error, error_string):
        if error == QMediaPlayer.Error.NoError:
            return
        message = error_string or "Qt Multimedia could not play this WebM file."
        self.error = f"WebM playback failed: {message}"
        log_warning("%s", self.error)
        self.error_changed.emit(self.error)
