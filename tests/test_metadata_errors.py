import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from types import SimpleNamespace

import pytest
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from openanima_app.assets.models import AssetType
from openanima_app.assets.validation import validate_asset_metadata


@pytest.fixture(scope="module", autouse=True)
def application():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.mark.parametrize("asset_type", [AssetType.SPRITE_STRIP, AssetType.SPRITESHEET])
def test_missing_image_field_is_distinct_from_missing_file(tmp_path, asset_type):
    asset = SimpleNamespace(type=asset_type, path=tmp_path, metadata={})
    [error] = validate_asset_metadata(asset)
    assert "metadata" in error and "image" in error
    assert "Select" in error
    asset.metadata = {"image": "missing.png"}
    [error] = validate_asset_metadata(asset)
    assert "missing.png" in error
    assert "Select" in error


@pytest.mark.parametrize("metadata, fields", [
    ({"frame_height": 8}, "frame_width"),
    ({"frame_width": 8}, "frame_height"),
    ({}, "frame_width, frame_height"),
    ({"frame_width": -1, "frame_height": 8}, "frame_width"),
])
def test_spritesheet_names_invalid_dimensions(tmp_path, metadata, fields):
    image = QImage(16, 16, QImage.Format_RGBA8888)
    image.fill(0)
    assert image.save(str(tmp_path / "sheet.png"))
    asset = SimpleNamespace(type=AssetType.SPRITESHEET, path=tmp_path,
        metadata={"image": "sheet.png", "animations": {"idle": {"frames": [{"col": 0, "row": 0}]}}, **metadata})
    [error] = validate_asset_metadata(asset)
    assert fields in error and "Set" in error
