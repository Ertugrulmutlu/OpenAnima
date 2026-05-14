from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QImageReader, QMovie, QPixmap

from ..ui.styles import THUMBNAIL_SIZE
from .models import AssetDefinition


def make_thumbnail(asset_or_path):
    path = asset_or_path.preview_path if isinstance(asset_or_path, AssetDefinition) else asset_or_path
    reader = QImageReader(str(path))
    if Path(path).suffix.lower() == ".apng":
        reader.setFormat(b"png")
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
