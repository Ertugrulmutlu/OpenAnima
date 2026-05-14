import os
import shutil
import uuid
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from openanima_app.runtime import state
from openanima_app.assets.analyzer import APNG_TYPE, SPRITESHEET_TYPE, AssetAnalyzer, AssetGuess
from openanima_app.ui.asset_setup.dialog import AssetSetupDialog
from openanima_app.assets import AssetType, detect_asset, import_asset_to_assets, is_supported_asset_file


def runtime_dir():
    path = Path(".test_runtime_tmp") / uuid.uuid4().hex
    path.mkdir(parents=True)
    return path


def app_instance():
    return QApplication.instance() or QApplication([])


def test_apng_is_detected_as_supported_asset():
    root = runtime_dir()
    try:
        path = root / "sample.apng"
        path.write_bytes(b"not a real image")

        guesses = AssetAnalyzer().analyze_file(path)
        asset = detect_asset(path)

        assert is_supported_asset_file(path)
        assert guesses[0].guessed_type == AssetType.APNG
        assert asset is not None
        assert asset.type == AssetType.APNG
    finally:
        shutil.rmtree(root)


def test_webm_is_detected_with_video_metadata():
    root = runtime_dir()
    try:
        path = root / "clip.webm"
        path.write_bytes(b"not a real video")

        guesses = AssetAnalyzer().analyze_file(path)
        asset = detect_asset(path)

        assert is_supported_asset_file(path)
        assert guesses[0].guessed_type == AssetType.WEBM
        assert "WebM playback uses Qt Multimedia" in " ".join(guesses[0].reasons)
        assert guesses[0].suggested_metadata == {"type": AssetType.WEBM, "video": path.name}
        assert asset is not None
        assert asset.type == AssetType.WEBM
    finally:
        shutil.rmtree(root)


def test_webm_likely_alpha_metadata_is_detected():
    root = runtime_dir()
    try:
        path = root / "transparent.webm"
        path.write_bytes(b"\x1a\x45\xdf\xa3fake-webm" + b"\x53\xc0\x81\x01")

        guesses = AssetAnalyzer().analyze_file(path)

        assert guesses[0].guessed_type == AssetType.WEBM
        assert guesses[0].suggested_metadata == {"type": AssetType.WEBM, "video": path.name, "likely_alpha": True}
        assert "alpha transparency" in " ".join(guesses[0].reasons)
    finally:
        shutil.rmtree(root)


def test_png_apng_chunk_takes_priority_over_spritesheet_guess():
    root = runtime_dir()
    try:
        path = root / "ezgif-com-apng-maker.png"
        path.write_bytes(minimal_apng_bytes(width=32, height=32))

        guesses = AssetAnalyzer().analyze_file(path)
        metadata = guesses[0].suggested_metadata
        asset = detect_asset(path)

        assert guesses[0].guessed_type == AssetType.APNG
        assert metadata == {"type": AssetType.APNG, "image": path.name}
        assert "frame_width" not in metadata
        assert "frame_height" not in metadata
        assert "note" not in metadata
        assert asset is not None
        assert asset.type == AssetType.APNG
    finally:
        shutil.rmtree(root)


def test_normal_png_without_actl_is_not_apng():
    root = runtime_dir()
    try:
        path = root / "normal.png"
        path.write_bytes(minimal_png_bytes(width=1, height=1))

        guesses = AssetAnalyzer().analyze_file(path)
        asset = detect_asset(path)

        assert guesses[0].guessed_type == AssetType.STATIC_IMAGE
        assert asset is not None
        assert asset.type == AssetType.STATIC_IMAGE
    finally:
        shutil.rmtree(root)


def test_imported_png_apng_reload_keeps_apng_type():
    root = runtime_dir()
    old_assets_dir = state.ASSETS_DIR
    try:
        source = root / "ezgif-com-apng-maker.png"
        source.write_bytes(minimal_apng_bytes(width=32, height=32))
        state.ASSETS_DIR = root / "assets"

        imported = import_asset_to_assets(source)
        first_load = detect_asset(imported)
        reload_load = detect_asset(imported)

        assert imported is not None
        assert first_load is not None
        assert first_load.type == AssetType.APNG
        assert reload_load is not None
        assert reload_load.type == AssetType.APNG
    finally:
        state.ASSETS_DIR = old_assets_dir
        shutil.rmtree(root)


def test_apng_dialog_metadata_is_clean_even_if_selected_guess_is_not_apng():
    app_instance()
    root = runtime_dir()
    try:
        path = root / "ezgif-com-apng-maker.png"
        path.write_bytes(minimal_apng_bytes(width=32, height=32))
        guesses = [
            AssetGuess(
                guessed_type=SPRITESHEET_TYPE,
                confidence=0.74,
                reasons=["Old heuristic result."],
                suggested_metadata={
                    "type": SPRITESHEET_TYPE,
                    "image": path.name,
                    "frame_width": 16,
                    "frame_height": 16,
                    "note": "Needs animation frame selection",
                },
            ),
            AssetGuess(
                guessed_type=APNG_TYPE,
                confidence=1.0,
                reasons=["APNG result."],
                suggested_metadata={"type": APNG_TYPE, "image": path.name},
            ),
        ]
        dialog = AssetSetupDialog(path, guesses)
        dialog.type_combo.setCurrentText(AssetType.APNG)
        dialog.guess_list.setCurrentRow(0)

        metadata = dialog.metadata()

        assert metadata == {"type": AssetType.APNG, "name": path.stem, "image": path.name}
        assert "frame_width" not in metadata
        assert "frame_height" not in metadata
        assert "note" not in metadata
        dialog.deleteLater()
    finally:
        shutil.rmtree(root)


def minimal_apng_bytes(width=16, height=16):
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = (
        width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"\x08\x06\x00\x00\x00"
    )
    actl = (1).to_bytes(4, "big") + (0).to_bytes(4, "big")
    return signature + png_chunk(b"IHDR", ihdr) + png_chunk(b"acTL", actl) + png_chunk(b"IEND", b"")


def minimal_png_bytes(width=1, height=1):
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = (
        width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"\x08\x06\x00\x00\x00"
    )
    return signature + png_chunk(b"IHDR", ihdr) + png_chunk(b"IEND", b"")


def png_chunk(chunk_type, data):
    import zlib

    payload = chunk_type + data
    return len(data).to_bytes(4, "big") + payload + zlib.crc32(payload).to_bytes(4, "big")
