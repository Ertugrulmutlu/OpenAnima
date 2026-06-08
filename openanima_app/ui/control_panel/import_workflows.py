import json
from pathlib import Path

from PySide6.QtCore import QCoreApplication
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
    dialog_title = QCoreApplication.translate("AssetImporter", "Import Asset")
    file_filter = QCoreApplication.translate("AssetImporter", "Visual assets (*.gif *.apng *.png *.jpg *.jpeg *.webp *.webm)")
    
    path, _ = QFileDialog.getOpenFileName(
        panel,
        dialog_title,
        str(BASE_DIR),
        file_filter,
    )
    if not path:
        return

    panel.import_analyzed_path(Path(path))


def import_folder(panel):
    dialog_title = QCoreApplication.translate("AssetImporter", "Import Asset Folder")
    path = QFileDialog.getExistingDirectory(panel, dialog_title, str(BASE_DIR))
    if not path:
        return
    panel.import_analyzed_path(Path(path))


def import_pack(panel):
    dialog_title = QCoreApplication.translate("AssetImporter", "Import Asset Pack")
    file_filter = QCoreApplication.translate("AssetImporter", "Asset packs (*.zip);;All files (*)")
    
    path, _ = QFileDialog.getOpenFileName(
        panel,
        dialog_title,
        str(BASE_DIR),
        file_filter,
    )
    if not path:
        folder_title = QCoreApplication.translate("AssetImporter", "Import Asset Pack Folder")
        folder = QFileDialog.getExistingDirectory(panel, folder_title, str(BASE_DIR))
        path = folder
    if not path:
        return

    panel.import_asset_pack_path(Path(path))


def import_asset_pack_path(panel, path):
    dialog_title = QCoreApplication.translate("AssetImporter", "Import Asset Pack")
    try:
        result = import_asset_pack(Path(path), state.ASSETS_DIR)
    except Exception as exc:
        log_warning("Asset pack import failed for %s: %s", path, exc)
        err_msg = QCoreApplication.translate("AssetImporter", "This asset pack could not be imported.")
        QMessageBox.warning(panel, dialog_title, err_msg)
        return

    panel.refresh_packs()
    index = panel.pack_combo.findData(str(result.path))
    if index >= 0:
        panel.pack_combo.setCurrentIndex(index)
        
    fallback_details = QCoreApplication.translate("AssetImporter", "No supported assets were detected yet.")
    details = "\n".join(result.detected_assets[:12]) or fallback_details
    
    if len(result.detected_assets) > 12:
        more_prefix = QCoreApplication.translate("AssetImporter", "...and")
        more_suffix = QCoreApplication.translate("AssetImporter", "more")
        details += f"\n{more_prefix} {len(result.detected_assets) - 12} {more_suffix}"
        
    report_msg = QCoreApplication.translate("AssetImporter", "Imported {pack_name}.\n\nDetected assets:\n{pack_details}")
    QMessageBox.information(
        panel,
        dialog_title,
        report_msg.format(pack_name=result.name, pack_details=details),
    )


def import_analyzed_path(panel, path, add_to_desktop=False):
    dialog_title = QCoreApplication.translate("AssetImporter", "Import Asset")
    analyzer = AssetAnalyzer()
    guesses = analyzer.analyze_path(path)
    if not guesses:
        log_warning("No supported asset type could be guessed for import path: %s", path)
        unsupported_msg = QCoreApplication.translate("AssetImporter", "This file or folder is not a supported OpenAnima asset.")
        QMessageBox.warning(panel, dialog_title, unsupported_msg)
        return

    if add_to_desktop:
        btn_text = QCoreApplication.translate("AssetImporter", "Add to Desktop")
    else:
        btn_text = QCoreApplication.translate("AssetImporter", "Import Asset")

    dialog = AssetSetupDialog(
        path,
        guesses,
        parent=panel,
        primary_button_text=btn_text,
    )
    if dialog.exec() != QDialog.Accepted:
        return

    imported = panel.create_import_from_setup(Path(path), dialog.metadata(), dialog.asset_name())
    if imported is None:
        log_warning("Selected asset could not be imported: %s", path)
        load_err = QCoreApplication.translate("AssetImporter", "This file could not be loaded.")
        QMessageBox.warning(panel, dialog_title, load_err)
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
        dialog_title = QCoreApplication.translate("AssetImporter", "Import Asset")
        warning_msg = QCoreApplication.translate("AssetImporter", "Some files are not supported:\n")
        QMessageBox.warning(
            panel,
            dialog_title,
            warning_msg + "\n".join(unsupported[:8]),
        )


def create_import_from_setup(panel, path: Path, metadata: dict, asset_name: str):
    asset_type = metadata.get("type")
    if path.is_file() and asset_type in {AssetType.GIF, AssetType.APNG, AssetType.WEBM, AssetType.STATIC_IMAGE}:
        return import_asset_to_assets(path, panel.active_pack_dir())

    reason_text = QCoreApplication.translate("AssetImporter", "Confirmed in Asset Setup.")
    guess = AssetGuess(
        guessed_type=str(asset_type),
        confidence=1.0,
        reasons=[reason_text],
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
        reason_existing = QCoreApplication.translate("AssetImporter", "Existing asset type.")
        guesses = [
            AssetGuess(
                guessed_type=asset.type,
                confidence=1.0,
                reasons=[reason_existing],
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
        dialog_title = QCoreApplication.translate("AssetImporter", "Edit Asset Metadata")
        save_err = QCoreApplication.translate("AssetImporter", "This asset metadata could not be saved.")
        QMessageBox.warning(panel, dialog_title, save_err)
        return

    panel.refresh_packs()
    panel.select_imported_library_item(saved_path)
    panel.offer_reload_running_overlays(saved_path)


def save_asset_metadata(panel, path: Path, metadata: dict, asset_name: str):
    asset_type = metadata.get("type")
    dialog_title = QCoreApplication.translate("AssetImporter", "Edit Asset Metadata")
    
    if path.is_dir():
        if asset_type in {AssetType.GIF, AssetType.APNG, AssetType.WEBM, AssetType.STATIC_IMAGE}:
            return path
        metadata_path = path / "asset.json"
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        asset = detect_asset(path)
        
        fallback_validation_err = QCoreApplication.translate("AssetImporter", "Unable to read saved asset metadata.")
        errors = validate_asset_metadata(asset) if asset is not None else [fallback_validation_err]
        if errors:
            log_warning("Saved asset metadata has validation errors for %s: %s", path, "; ".join(errors))
            QMessageBox.warning(panel, dialog_title, "\n".join(errors))
        return path

    if asset_type in {AssetType.GIF, AssetType.APNG, AssetType.WEBM, AssetType.STATIC_IMAGE}:
        return path

    reason_configured = QCoreApplication.translate("AssetImporter", "Configured from an existing file asset.")
    guess = AssetGuess(
        guessed_type=str(asset_type),
        confidence=1.0,
        reasons=[reason_configured],
        suggested_metadata=metadata,
    )
    return create_asset_folder_from_guess(path, panel.active_pack_dir(), guess, asset_name)


def offer_reload_running_overlays(panel, asset_path):
    asset_path = Path(asset_path).resolve()
    matching = [window for window in state.WINDOWS if Path(window.asset_path).resolve() == asset_path]
    if not matching:
        return

    dialog_title = QCoreApplication.translate("AssetImporter", "Reload Asset")
    question_text = QCoreApplication.translate("AssetImporter", "Reload running overlays for this asset?")
    
    result = QMessageBox.question(
        panel,
        dialog_title,
        question_text,
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.Yes,
    )
    if result != QMessageBox.Yes:
        return

    asset = detect_asset(asset_path)
    if asset is None:
        log_warning("Unable to reload asset definition: %s", asset_path)
        err_msg = QCoreApplication.translate("AssetImporter", "Unable to reload this asset definition.")
        QMessageBox.warning(panel, dialog_title, err_msg)
        return

    failed = []
    for window in matching:
        if not window.reload_asset_definition(asset):
            failed.append(window.asset.name)
    if failed:
        log_warning("Some overlays could not be reloaded for asset %s: %s", asset_path, ", ".join(failed))
        partial_err = QCoreApplication.translate("AssetImporter", "Some overlays could not be reloaded and were kept unchanged.")
        QMessageBox.warning(panel, dialog_title, partial_err)
        
    panel.refresh_active()
    if panel.selected_window in state.WINDOWS:
        panel.load_editor(panel.selected_window)
