import json
import shutil
import uuid
from pathlib import Path

from openanima_app.assets.pack_importer import import_asset_pack


def runtime_dir():
    path = Path(".test_runtime_tmp") / uuid.uuid4().hex
    path.mkdir(parents=True)
    return path


def test_import_asset_pack_folder_reads_pack_metadata_and_detects_assets():
    root = runtime_dir()
    try:
        source = root / "source_pack"
        target_root = root / "assets"
        source.mkdir()
        (source / "pack.json").write_text(
            json.dumps({"name": "Local Pack", "author": "Tester", "assets": ["sticker.png"]}),
            encoding="utf-8",
        )
        (source / "sticker.png").write_bytes(b"not a real image")

        result = import_asset_pack(source, target_root)

        assert result.name == "Local Pack"
        assert result.author == "Tester"
        assert result.path.parent == target_root.resolve()
        assert result.detected_assets == ["sticker.png"]
        assert (result.path / "pack.json").exists()
    finally:
        shutil.rmtree(root)
