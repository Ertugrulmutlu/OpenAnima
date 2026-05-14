import json
from pathlib import Path

from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

from ...assets.analyzer import AssetAnalyzer, AssetGuess, create_asset_folder_from_guess
from ...assets.detection import detect_asset
from ...assets.importer import import_asset_to_assets
from ...assets.metadata import load_metadata
from ...assets.models import AssetType
from ...assets.pack_importer import import_asset_pack
from ...assets.validation import validate_asset_metadata
from ...overlay import add_window
from ...runtime import state
from ...runtime.logging import log_warning
from ...runtime.paths import BASE_DIR
from ..asset_setup.dialog import AssetSetupDialog


def import_asset(panel):
    path, _ = QFileDialog.getOpenFileName(
        panel,
        "Import Asset",
        str(BASE_DIR),
        "Visual assets (*.gif *.apng *.png *.jpg *.jpeg *.webp *.webm)",
    )
    if not path:
        return

    panel.import_analyzed_path(Path(path))


def import_folder(panel):
    path = QFileDialog.getExistingDirectory(panel, "Import Asset Folder", str(BASE_DIR))
    if not path:
        return
    panel.import_analyzed_path(Path(path))


def import_pack(panel):
    path, _ = QFileDialog.getOpenFileName(
        panel,
        "Import Asset Pack",
        str(BASE_DIR),
        "Asset packs (*.zip);;All files (*)",
    )
    if not path:
        folder = QFileDialog.getExistingDirectory(panel, "Import Asset Pack Folder", str(BASE_DIR))
        path = folder
    if not path:
        return

    panel.import_asset_pack_path(Path(path))


def import_asset_pack_path(panel, path):
    try:
        result = import_asset_pack(Path(path), state.ASSETS_DIR)
    except Exception as exc:
        log_warning("Asset pack import failed for %s: %s", path, exc)
        QMessageBox.warning(panel, "Import Asset Pack", "This asset pack could not be imported.")
        return

    panel.refresh_packs()
    index = panel.pack_combo.findData(str(result.path))
    if index >= 0:
        panel.pack_combo.setCurrentIndex(index)
    details = "\n".join(result.detected_assets[:12]) or "No supported assets were detected yet."
    if len(result.detected_assets) > 12:
        details += f"\n...and {len(result.detected_assets) - 12} more"
    QMessageBox.information(
        panel,
        "Import Asset Pack",
        f"Imported {result.name}.\n\nDetected assets:\n{details}",
    )


def import_analyzed_path(panel, path, add_to_desktop=False):
    analyzer = AssetAnalyzer()
    guesses = analyzer.analyze_path(path)
    if not guesses:
        log_warning("No supported asset type could be guessed for import path: %s", path)
        QMessageBox.warning(panel, "Import Asset", "This file or folder is not a supported OpenAnima asset.")
        return

    dialog = AssetSetupDialog(
        path,
        guesses,
        parent=panel,
        primary_button_text="Add to Desktop" if add_to_desktop else "Import Asset",
    )
    if dialog.exec() != QDialog.Accepted:
        return

    imported = panel.create_import_from_setup(Path(path), dialog.metadata(), dialog.asset_name())
    if imported is None:
        log_warning("Selected asset could not be imported: %s", path)
        QMessageBox.warning(panel, "Import Asset", "This file could not be loaded.")
        return

    panel.refresh_packs()
    panel.select_imported_library_item(imported)
    if add_to_desktop:
        window = add_window(imported)
        if window is not None:
            panel.select_window(window)


def import_dropped_paths(panel, paths):
    unsupported = []
    for path in paths:
        path = Path(path)
        if path.suffix.lower() == ".zip":
            panel.import_asset_pack_path(path)
            continue
        analyzer = AssetAnalyzer()
        guesses = analyzer.analyze_path(path)
        if guesses:
            panel.import_analyzed_path(path)
            continue
        if path.is_dir():
            panel.import_asset_pack_path(path)
            continue
        unsupported.append(path.name)
    if unsupported:
        QMessageBox.warning(
            panel,
            "Import Asset",
            "Some files are not supported:\n" + "\n".join(unsupported[:8]),
        )


def create_import_from_setup(panel, path: Path, metadata: dict, asset_name: str):
    asset_type = metadata.get("type")
    if path.is_file() and asset_type in {AssetType.GIF, AssetType.APNG, AssetType.WEBM, AssetType.STATIC_IMAGE}:
        return import_asset_to_assets(path, panel.active_pack_dir())

    guess = AssetGuess(
        guessed_type=str(asset_type),
        confidence=1.0,
        reasons=["Confirmed in Asset Setup."],
        suggested_metadata=metadata,
    )
    return create_asset_folder_from_guess(path, panel.active_pack_dir(), guess, asset_name)


def configure_selected_library_asset(panel):
    path = panel.library_path_from_current_item()
    if path is None:
        return
    panel.configure_asset_path(path)


def configure_active_asset(panel):
    window = panel.window_from_current_item()
    if window is None:
        return
    panel.configure_asset_path(window.asset.path)


def configure_selected_overlay_asset(panel):
    if panel.selected_window not in state.WINDOWS:
        return
    panel.configure_asset_path(panel.selected_window.asset.path)


def configure_asset_path(panel, path):
    path = Path(path).resolve()
    analyzer = AssetAnalyzer()
    guesses = analyzer.analyze_path(path)
    metadata = load_metadata(path) if path.is_dir() else {}
    asset = detect_asset(path)
    if asset is not None and not metadata:
        metadata = {"type": asset.type, "name": asset.name}

    if not guesses and asset is not None:
        guesses = [
            AssetGuess(
                guessed_type=asset.type,
                confidence=1.0,
                reasons=["Existing asset type."],
                suggested_metadata=metadata,
            )
        ]

    dialog = AssetSetupDialog(path, guesses, existing_metadata=metadata, parent=panel)
    if dialog.exec() != QDialog.Accepted:
        return

    new_metadata = dialog.metadata()
    saved_path = panel.save_asset_metadata(path, new_metadata, dialog.asset_name())
    if saved_path is None:
        log_warning("Asset metadata could not be saved: %s", path)
        QMessageBox.warning(panel, "Edit Asset Metadata", "This asset metadata could not be saved.")
        return

    panel.refresh_packs()
    panel.select_imported_library_item(saved_path)
    panel.offer_reload_running_overlays(saved_path)


def save_asset_metadata(panel, path: Path, metadata: dict, asset_name: str):
    asset_type = metadata.get("type")
    if path.is_dir():
        if asset_type in {AssetType.GIF, AssetType.APNG, AssetType.WEBM, AssetType.STATIC_IMAGE}:
            return path
        metadata_path = path / "asset.json"
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        asset = detect_asset(path)
        errors = validate_asset_metadata(asset) if asset is not None else ["Unable to read saved asset metadata."]
        if errors:
            log_warning("Saved asset metadata has validation errors for %s: %s", path, "; ".join(errors))
            QMessageBox.warning(panel, "Edit Asset Metadata", "\n".join(errors))
        return path

    if asset_type in {AssetType.GIF, AssetType.APNG, AssetType.WEBM, AssetType.STATIC_IMAGE}:
        return path

    guess = AssetGuess(
        guessed_type=str(asset_type),
        confidence=1.0,
        reasons=["Configured from an existing file asset."],
        suggested_metadata=metadata,
    )
    return create_asset_folder_from_guess(path, panel.active_pack_dir(), guess, asset_name)


def offer_reload_running_overlays(panel, asset_path):
    asset_path = Path(asset_path).resolve()
    matching = [window for window in state.WINDOWS if Path(window.asset_path).resolve() == asset_path]
    if not matching:
        return

    result = QMessageBox.question(
        panel,
        "Reload Asset",
        "Reload running overlays for this asset?",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.Yes,
    )
    if result != QMessageBox.Yes:
        return

    asset = detect_asset(asset_path)
    if asset is None:
        log_warning("Unable to reload asset definition: %s", asset_path)
        QMessageBox.warning(panel, "Reload Asset", "Unable to reload this asset definition.")
        return

    failed = []
    for window in matching:
        if not window.reload_asset_definition(asset):
            failed.append(window.asset.name)
    if failed:
        log_warning("Some overlays could not be reloaded for asset %s: %s", asset_path, ", ".join(failed))
        QMessageBox.warning(panel, "Reload Asset", "Some overlays could not be reloaded and were kept unchanged.")
    panel.refresh_active()
    if panel.selected_window in state.WINDOWS:
        panel.load_editor(panel.selected_window)
