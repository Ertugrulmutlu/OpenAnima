import os
import shutil
import uuid
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from openanima_app.rendering.video_renderer import DEFAULT_VIDEO_SIZE, VideoAssetRenderer
from openanima_app.rendering.webm import webm_likely_has_alpha


def runtime_dir():
    path = Path(".test_runtime_tmp") / uuid.uuid4().hex
    path.mkdir(parents=True)
    return path


def app_instance():
    return QApplication.instance() or QApplication([])


def test_webm_renderer_can_be_created_without_playback_crash():
    app_instance()
    root = runtime_dir()
    try:
        path = root / "clip.webm"
        path.write_bytes(b"not a real webm")

        renderer = VideoAssetRenderer(path)
        pixmap = renderer.placeholder_pixmap()

        assert renderer.path == path
        assert pixmap.width() == DEFAULT_VIDEO_SIZE[0]
        assert pixmap.height() == DEFAULT_VIDEO_SIZE[1]
        renderer.release()
        renderer.deleteLater()
    finally:
        shutil.rmtree(root)


def test_webm_alpha_detector_reads_alpha_mode_element():
    root = runtime_dir()
    try:
        normal = root / "normal.webm"
        alpha = root / "alpha.webm"
        normal.write_bytes(b"\x1a\x45\xdf\xa3fake-webm")
        alpha.write_bytes(b"\x1a\x45\xdf\xa3fake-webm" + b"\x53\xc0\x81\x01")

        assert webm_likely_has_alpha(normal) is False
        assert webm_likely_has_alpha(alpha) is True
    finally:
        shutil.rmtree(root)


def test_renderer_warns_when_webm_likely_has_alpha():
    app_instance()
    root = runtime_dir()
    try:
        path = root / "alpha.webm"
        path.write_bytes(b"\x1a\x45\xdf\xa3fake-webm" + b"\x53\xc0\x81\x01")
        renderer = VideoAssetRenderer(path)
        warnings = []
        renderer.warning_changed.connect(warnings.append)

        from PySide6.QtGui import QImage

        image = QImage(2, 2, QImage.Format_RGB32)
        renderer.check_alpha_support(image)

        assert warnings == ["Transparent WebM alpha may not be preserved by your current Qt video backend."]
        assert renderer.alpha_supported is False
        renderer.release()
        renderer.deleteLater()
    finally:
        shutil.rmtree(root)
