import json
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QTextEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from . import state
from .asset_analyzer import (
    AssetAnalyzer,
    AssetGuess,
    create_asset_folder_from_guess,
)
from .asset_setup_dialog import AssetSetupDialog
from .asset_validation import validate_asset_metadata
from .assets import (
    AssetType,
    assets_for_pack,
    asset_packs,
    detect_asset,
    import_asset_to_assets,
    load_metadata,
    make_thumbnail,
    save_config,
)
from .constants import BASE_DIR, CONFIG_PATH, LOG_DIR, LOG_PATH, THUMBNAIL_SIZE
from .logging_utils import log_warning, recent_warnings_and_errors
from .overlay import add_window, confirm_exit_or_tray
from .startup import set_startup_enabled, startup_enabled
from .version import __version__


class ControlPanel(QWidget):
    def __init__(self, app_icon=None):
        super().__init__()
        self.selected_window = None
        self.loading_editor = False
        self.editor_tab = None
        self.editor_tab_index = -1
        self.tray_icon = None
        self.layer_value_sliders = {}

        self.setWindowTitle("OpenAnima Control Panel")
        if app_icon is not None and not app_icon.isNull():
            self.setWindowIcon(app_icon)
        self.setMinimumSize(660, 520)

        self.tabs = QTabWidget()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addWidget(self.tabs)

        self.build_library_tab()
        self.build_active_tab()
        self.build_diagnostics_tab()
        self.build_editor_tab()
        self.tabs.currentChanged.connect(lambda index: self.refresh_diagnostics())

        self.refresh_packs()
        self.refresh_active()
        self.refresh_diagnostics()
        self.load_editor(None)

    def panel(self):
        frame = QFrame()
        frame.setObjectName("Panel")
        frame.setFrameShape(QFrame.NoFrame)
        return frame

    def build_library_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Library")
        title.setObjectName("SectionTitle")
        subtitle = QLabel("Choose an asset pack and add visual assets to the desktop.")
        subtitle.setObjectName("SubtleLabel")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        self.pack_combo = QComboBox()
        self.pack_combo.currentIndexChanged.connect(self.refresh_library)

        header.addLayout(title_box, 1)
        header.addWidget(QLabel("Pack"))
        header.addWidget(self.pack_combo)

        root_row = QHBoxLayout()
        self.asset_root_label = QLabel()
        self.asset_root_label.setObjectName("SubtleLabel")
        change_root_button = QPushButton("Change Assets Folder")
        change_root_button.clicked.connect(self.change_asset_root)
        root_row.addWidget(self.asset_root_label, 1)
        root_row.addWidget(change_root_button)

        self.library_list = QListWidget()
        self.library_list.setViewMode(QListView.IconMode)
        self.library_list.setMovement(QListView.Static)
        self.library_list.setResizeMode(QListView.Adjust)
        self.library_list.setIconSize(THUMBNAIL_SIZE)
        self.library_list.setGridSize(QSize(132, 142))
        self.library_list.setSpacing(8)
        self.library_list.setUniformItemSizes(True)
        self.library_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.library_list.itemDoubleClicked.connect(lambda item: self.add_selected_library_asset())
        self.library_list.customContextMenuRequested.connect(self.open_library_menu)

        buttons = QHBoxLayout()
        import_button = QPushButton("Import Asset")
        import_folder_button = QPushButton("Import Folder")
        configure_button = QPushButton("Configure Asset")
        add_button = QPushButton("Add to Desktop")
        import_button.clicked.connect(self.import_asset)
        import_folder_button.clicked.connect(self.import_folder)
        configure_button.clicked.connect(self.configure_selected_library_asset)
        add_button.clicked.connect(self.add_selected_library_asset)
        buttons.addWidget(import_button)
        buttons.addWidget(import_folder_button)
        buttons.addStretch()
        buttons.addWidget(configure_button)
        buttons.addWidget(add_button)

        layout.addLayout(header)
        layout.addLayout(root_row)
        layout.addWidget(self.library_list, 1)
        layout.addLayout(buttons)
        self.tabs.addTab(tab, "Library")

    def build_active_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Active Assets")
        title.setObjectName("SectionTitle")
        subtitle = QLabel("Select a running overlay to edit, lock, or close it.")
        subtitle.setObjectName("SubtleLabel")

        self.active_list = QListWidget()
        self.active_list.setIconSize(QSize(56, 56))
        self.active_list.setSpacing(6)
        self.active_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.active_list.itemDoubleClicked.connect(lambda item: self.select_active())
        self.active_list.customContextMenuRequested.connect(self.open_active_menu)

        buttons = QHBoxLayout()
        select_button = QPushButton("Edit Selected")
        configure_button = QPushButton("Configure Asset")
        close_button = QPushButton("Close Selected")
        lock_button = QPushButton("Lock/Unlock")
        hide_all_button = QPushButton("Hide all overlays")
        show_all_button = QPushButton("Show all overlays")

        select_button.clicked.connect(self.select_active)
        configure_button.clicked.connect(self.configure_active_asset)
        close_button.clicked.connect(self.close_active)
        lock_button.clicked.connect(self.toggle_active_lock)
        hide_all_button.clicked.connect(self.hide_all_overlays)
        show_all_button.clicked.connect(self.show_all_overlays)

        buttons.addWidget(select_button)
        buttons.addWidget(configure_button)
        buttons.addWidget(lock_button)
        buttons.addWidget(close_button)
        buttons.addStretch()
        buttons.addWidget(hide_all_button)
        buttons.addWidget(show_all_button)

        self.startup_check = QCheckBox("Start on system boot")
        self.startup_check.setEnabled(False)
        if hasattr(self.startup_check, "setVisible"):
            import sys

            self.startup_check.setVisible(sys.platform == "win32")
            if sys.platform == "win32":
                self.startup_check.setEnabled(True)
                self.startup_check.setChecked(startup_enabled())
                self.startup_check.toggled.connect(set_startup_enabled)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.active_list, 1)
        layout.addLayout(buttons)
        layout.addWidget(self.startup_check)
        self.tabs.addTab(tab, "Active")

    def build_diagnostics_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Diagnostics")
        title.setObjectName("SectionTitle")
        subtitle = QLabel("Review runtime paths, active overlays, and recent warnings.")
        subtitle.setObjectName("SubtleLabel")

        info_panel = self.panel()
        info_layout = QVBoxLayout(info_panel)
        info_layout.setContentsMargins(14, 14, 14, 14)
        info_layout.setSpacing(8)

        self.diagnostics_version = QLabel()
        self.diagnostics_config_path = QLabel()
        self.diagnostics_asset_root = QLabel()
        self.diagnostics_log_path = QLabel()
        self.diagnostics_overlay_count = QLabel()
        for label in (
            self.diagnostics_version,
            self.diagnostics_config_path,
            self.diagnostics_asset_root,
            self.diagnostics_log_path,
            self.diagnostics_overlay_count,
        ):
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            label.setWordWrap(True)
            info_layout.addWidget(label)

        warnings_label = QLabel("Recent warnings/errors")
        warnings_label.setObjectName("SubtleLabel")
        self.diagnostics_recent = QTextEdit()
        self.diagnostics_recent.setReadOnly(True)
        self.diagnostics_recent.setMinimumHeight(160)

        buttons = QHBoxLayout()
        open_logs_button = QPushButton("Open Logs Folder")
        copy_button = QPushButton("Copy Diagnostic Info")
        refresh_button = QPushButton("Refresh")
        open_logs_button.clicked.connect(self.open_logs_folder)
        copy_button.clicked.connect(self.copy_diagnostics)
        refresh_button.clicked.connect(self.refresh_diagnostics)
        buttons.addWidget(open_logs_button)
        buttons.addWidget(copy_button)
        buttons.addStretch()
        buttons.addWidget(refresh_button)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(info_panel)
        layout.addWidget(warnings_label)
        layout.addWidget(self.diagnostics_recent, 1)
        layout.addLayout(buttons)
        self.tabs.addTab(tab, "Diagnostics")

    def build_editor_tab(self):
        self.editor_tab = QWidget()
        layout = QVBoxLayout(self.editor_tab)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        layout.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(14)

        self.editor_placeholder = QLabel("Double click an asset to edit it")
        self.editor_placeholder.setObjectName("SubtleLabel")

        self.selected_group = QGroupBox("Selected Asset")
        selected_layout = QVBoxLayout(self.selected_group)
        selected_layout.setContentsMargins(14, 18, 14, 14)
        selected_layout.setSpacing(6)
        self.editor_name = QLabel("Double click an asset to edit it")
        self.editor_name.setObjectName("SubtleLabel")
        self.editor_type = QLabel("")
        self.editor_type.setObjectName("SubtleLabel")
        selected_layout.addWidget(self.editor_name)
        selected_layout.addWidget(self.editor_type)

        self.scale_label = QLabel("Scale: 100%")
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(50, 150)
        self.scale_slider.setTickInterval(10)
        self.scale_slider.valueChanged.connect(self.editor_scale_changed)

        self.opacity_label = QLabel("Opacity: 100%")
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(50, 100)
        self.opacity_slider.setTickInterval(10)
        self.opacity_slider.valueChanged.connect(self.editor_opacity_changed)

        self.speed_label = QLabel("Speed: 100%")
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(25, 200)
        self.speed_slider.setTickInterval(25)
        self.speed_slider.valueChanged.connect(self.editor_speed_changed)

        self.transform_group = QGroupBox("Transform")
        transform_layout = QVBoxLayout(self.transform_group)
        transform_layout.setContentsMargins(14, 18, 14, 14)
        transform_layout.setSpacing(12)
        transform_layout.addWidget(self.slider_row(self.scale_label, self.scale_slider))
        transform_layout.addWidget(self.slider_row(self.opacity_label, self.opacity_slider))
        self.speed_row = self.slider_row(self.speed_label, self.speed_slider)
        transform_layout.addWidget(self.speed_row)

        self.top_check = QCheckBox("Always on top")
        self.click_check = QCheckBox("Click-through")
        self.lock_check = QCheckBox("Locked")
        self.top_check.toggled.connect(self.editor_top_changed)
        self.click_check.toggled.connect(self.editor_click_changed)
        self.lock_check.toggled.connect(self.editor_lock_changed)

        self.reload_button = QPushButton("Reload Asset")
        self.reload_button.clicked.connect(self.reload_selected_asset)

        self.behavior_group = QGroupBox("Behavior")
        behavior_layout = QVBoxLayout(self.behavior_group)
        behavior_layout.setContentsMargins(14, 18, 14, 14)
        behavior_layout.setSpacing(10)
        behavior_layout.addWidget(self.top_check)
        behavior_layout.addWidget(self.click_check)
        behavior_layout.addWidget(self.lock_check)
        behavior_layout.addWidget(self.reload_button)

        self.spritesheet_group = QGroupBox("Spritesheet Controls")
        self.spritesheet_layout = QVBoxLayout(self.spritesheet_group)
        self.spritesheet_layout.setContentsMargins(14, 18, 14, 14)
        self.spritesheet_layout.setSpacing(10)

        self.composite_group = QGroupBox("Composite Values")
        self.composite_layout = QVBoxLayout(self.composite_group)
        self.composite_layout.setContentsMargins(14, 18, 14, 14)
        self.composite_layout.setSpacing(12)

        content_layout.addWidget(self.editor_placeholder)
        content_layout.addWidget(self.selected_group)
        content_layout.addWidget(self.transform_group)
        content_layout.addWidget(self.behavior_group)
        content_layout.addWidget(self.spritesheet_group)
        content_layout.addWidget(self.composite_group)
        content_layout.addStretch()

    def slider_row(self, value_label, slider):
        row = QWidget()
        layout = QVBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        value_label.setMinimumWidth(120)
        layout.addWidget(value_label)
        layout.addWidget(slider)
        return row

    def show_editor_tab(self):
        if self.editor_tab_index < 0:
            self.editor_tab_index = self.tabs.addTab(self.editor_tab, "Editor")
        self.tabs.setCurrentIndex(self.editor_tab_index)

    def hide_editor_tab(self):
        if self.editor_tab_index >= 0:
            self.tabs.removeTab(self.editor_tab_index)
            self.editor_tab_index = -1

    def active_pack_dir(self):
        return Path(self.pack_combo.currentData() or state.ASSETS_DIR)

    def refresh_packs(self):
        current = self.pack_combo.currentData()
        self.pack_combo.blockSignals(True)
        self.pack_combo.clear()

        for name, path in asset_packs():
            self.pack_combo.addItem(name, str(path))

        if current:
            index = self.pack_combo.findData(current)
            if index >= 0:
                self.pack_combo.setCurrentIndex(index)

        self.pack_combo.blockSignals(False)
        self.asset_root_label.setText(f"Assets: {state.ASSETS_DIR}")
        self.refresh_library()

    def change_asset_root(self):
        path = QFileDialog.getExistingDirectory(self, "Change Assets Folder", str(state.ASSETS_DIR))
        if not path:
            return

        state.ASSETS_DIR = Path(path).resolve()
        state.ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        save_config()
        self.refresh_packs()

    def refresh_library(self):
        if not hasattr(self, "library_list"):
            return

        self.library_list.clear()
        assets = assets_for_pack(self.active_pack_dir())
        if not assets:
            item = QListWidgetItem("No assets yet. Import an asset or place files in the assets folder.")
            item.setTextAlignment(Qt.AlignCenter)
            item.setFlags(Qt.NoItemFlags)
            self.library_list.addItem(item)
            return

        for asset in assets:
            item = QListWidgetItem(make_thumbnail(asset), asset.name)
            item.setTextAlignment(Qt.AlignHCenter | Qt.AlignBottom)
            item.setData(Qt.UserRole, str(asset.path))
            self.library_list.addItem(item)

    def refresh_active(self):
        selected_id = id(self.selected_window) if self.selected_window in state.WINDOWS else None
        self.active_list.clear()

        for window in state.WINDOWS:
            state_text = "locked" if window.locked else "unlocked"
            item = QListWidgetItem(make_thumbnail(window.asset), f"{window.asset.name}  -  {state_text}")
            item.setData(Qt.UserRole, id(window))
            self.active_list.addItem(item)
            if id(window) == selected_id:
                self.active_list.setCurrentItem(item)

        if self.selected_window not in state.WINDOWS:
            self.selected_window = None
            self.load_editor(None)
            self.hide_editor_tab()
        self.refresh_diagnostics()

    def refresh_diagnostics(self):
        if not hasattr(self, "diagnostics_recent"):
            return

        self.diagnostics_version.setText(f"Version: {__version__}")
        self.diagnostics_config_path.setText(f"Config: {CONFIG_PATH}")
        self.diagnostics_asset_root.setText(f"Assets: {state.ASSETS_DIR}")
        self.diagnostics_log_path.setText(f"Log file: {LOG_PATH}")
        self.diagnostics_overlay_count.setText(f"Active overlays: {len(state.WINDOWS)}")

        recent = recent_warnings_and_errors()
        if recent:
            lines = [f"{item['level']}: {item['message']}" for item in recent[-30:]]
            self.diagnostics_recent.setPlainText("\n".join(lines))
        else:
            self.diagnostics_recent.setPlainText("No warnings or errors recorded this session.")

    def diagnostics_text(self):
        recent = recent_warnings_and_errors()
        warnings = "\n".join(f"- {item['level']}: {item['message']}" for item in recent[-30:])
        if not warnings:
            warnings = "- None recorded this session."
        return "\n".join(
            [
                f"OpenAnima version: {__version__}",
                f"Config path: {CONFIG_PATH}",
                f"Asset root: {state.ASSETS_DIR}",
                f"Log file: {LOG_PATH}",
                f"Active overlays: {len(state.WINDOWS)}",
                "Recent warnings/errors:",
                warnings,
            ]
        )

    def open_logs_folder(self):
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(LOG_DIR))):
                raise OSError(f"Could not open {LOG_DIR}")
        except Exception as exc:
            log_warning("Unable to open logs folder: %s", exc)
            QMessageBox.warning(self, "Diagnostics", "Unable to open the logs folder.")

    def copy_diagnostics(self):
        QApplication.clipboard().setText(self.diagnostics_text())

    def window_from_current_item(self):
        item = self.active_list.currentItem()
        if item is None:
            return None
        window_id = item.data(Qt.UserRole)
        return next((window for window in state.WINDOWS if id(window) == window_id), None)

    def library_path_from_current_item(self):
        item = self.library_list.currentItem()
        if item is None or not item.data(Qt.UserRole):
            return None
        return Path(item.data(Qt.UserRole))

    def open_library_menu(self, pos):
        item = self.library_list.itemAt(pos)
        if item is None or not item.data(Qt.UserRole):
            return

        self.library_list.setCurrentItem(item)
        menu = QMenu(self)

        add_action = QAction("Add to Desktop", self)
        add_action.triggered.connect(self.add_selected_library_asset)
        menu.addAction(add_action)

        configure_action = QAction("Configure Asset", self)
        configure_action.triggered.connect(self.configure_selected_library_asset)
        menu.addAction(configure_action)

        menu.exec(self.library_list.mapToGlobal(pos))

    def open_active_menu(self, pos):
        item = self.active_list.itemAt(pos)
        if item is None:
            return

        self.active_list.setCurrentItem(item)
        menu = QMenu(self)

        edit_action = QAction("Edit", self)
        edit_action.triggered.connect(self.select_active)
        menu.addAction(edit_action)

        configure_action = QAction("Configure asset metadata", self)
        configure_action.triggered.connect(self.configure_active_asset)
        menu.addAction(configure_action)

        close_action = QAction("Close asset", self)
        close_action.triggered.connect(self.close_active)
        menu.addAction(close_action)

        menu.exec(self.active_list.mapToGlobal(pos))

    def import_asset(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Asset",
            str(BASE_DIR),
            "Visual assets (*.gif *.png *.jpg *.jpeg *.webp)",
        )
        if not path:
            return

        self.import_analyzed_path(Path(path))

    def import_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Import Asset Folder", str(BASE_DIR))
        if not path:
            return
        self.import_analyzed_path(Path(path))

    def import_analyzed_path(self, path):
        analyzer = AssetAnalyzer()
        guesses = analyzer.analyze_path(path)
        if not guesses:
            log_warning("No supported asset type could be guessed for import path: %s", path)
            QMessageBox.warning(self, "Import Asset", "No supported asset type could be guessed for this path.")
            return

        dialog = AssetSetupDialog(path, guesses, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return

        imported = self.create_import_from_setup(Path(path), dialog.metadata(), dialog.asset_name())
        if imported is None:
            log_warning("Selected asset could not be imported: %s", path)
            QMessageBox.warning(self, "Import Asset", "The selected asset could not be imported.")
            return

        self.refresh_packs()
        self.select_imported_library_item(imported)

    def create_import_from_setup(self, path: Path, metadata: dict, asset_name: str):
        asset_type = metadata.get("type")
        if path.is_file() and asset_type in {AssetType.GIF, AssetType.STATIC_IMAGE}:
            return import_asset_to_assets(path, self.active_pack_dir())

        guess = AssetGuess(
            guessed_type=str(asset_type),
            confidence=1.0,
            reasons=["Confirmed in Asset Setup."],
            suggested_metadata=metadata,
        )
        return create_asset_folder_from_guess(path, self.active_pack_dir(), guess, asset_name)

    def select_imported_library_item(self, imported):
        imported = Path(imported).resolve()
        for index in range(self.library_list.count()):
            item = self.library_list.item(index)
            item_path = item.data(Qt.UserRole)
            if item_path and Path(item_path).resolve() == imported:
                self.library_list.setCurrentItem(item)
                break

    def configure_selected_library_asset(self):
        path = self.library_path_from_current_item()
        if path is None:
            return
        self.configure_asset_path(path)

    def configure_active_asset(self):
        window = self.window_from_current_item()
        if window is None:
            return
        self.configure_asset_path(window.asset.path)

    def configure_asset_path(self, path):
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

        dialog = AssetSetupDialog(path, guesses, existing_metadata=metadata, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return

        new_metadata = dialog.metadata()
        saved_path = self.save_asset_metadata(path, new_metadata, dialog.asset_name())
        if saved_path is None:
            log_warning("Asset metadata could not be saved: %s", path)
            QMessageBox.warning(self, "Configure Asset", "This asset metadata could not be saved.")
            return

        self.refresh_packs()
        self.select_imported_library_item(saved_path)
        self.offer_reload_running_overlays(saved_path)

    def save_asset_metadata(self, path: Path, metadata: dict, asset_name: str):
        asset_type = metadata.get("type")
        if path.is_dir():
            if asset_type in {AssetType.GIF, AssetType.STATIC_IMAGE}:
                return path
            metadata_path = path / "asset.json"
            metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
            asset = detect_asset(path)
            errors = validate_asset_metadata(asset) if asset is not None else ["Unable to read saved asset metadata."]
            if errors:
                log_warning("Saved asset metadata has validation errors for %s: %s", path, "; ".join(errors))
                QMessageBox.warning(self, "Configure Asset", "\n".join(errors))
            return path

        if asset_type in {AssetType.GIF, AssetType.STATIC_IMAGE}:
            return path

        guess = AssetGuess(
            guessed_type=str(asset_type),
            confidence=1.0,
            reasons=["Configured from an existing file asset."],
            suggested_metadata=metadata,
        )
        return create_asset_folder_from_guess(path, self.active_pack_dir(), guess, asset_name)

    def offer_reload_running_overlays(self, asset_path):
        asset_path = Path(asset_path).resolve()
        matching = [window for window in state.WINDOWS if Path(window.asset_path).resolve() == asset_path]
        if not matching:
            return

        result = QMessageBox.question(
            self,
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
            QMessageBox.warning(self, "Reload Asset", "Unable to reload this asset definition.")
            return

        failed = []
        for window in matching:
            if not window.reload_asset_definition(asset):
                failed.append(window.asset.name)
        if failed:
            log_warning("Some overlays could not be reloaded for asset %s: %s", asset_path, ", ".join(failed))
            QMessageBox.warning(self, "Reload Asset", "Some overlays could not be reloaded and were kept unchanged.")
        self.refresh_active()
        if self.selected_window in state.WINDOWS:
            self.load_editor(self.selected_window)

    def add_selected_library_asset(self):
        item = self.library_list.currentItem()
        if item is not None and item.data(Qt.UserRole):
            add_window(item.data(Qt.UserRole))

    def hide_all_overlays(self):
        for window in state.WINDOWS:
            window.setVisible(False)

    def show_all_overlays(self):
        for window in state.WINDOWS:
            window.setVisible(True)
            window.raise_()

    def select_window(self, window):
        if window not in state.WINDOWS:
            return

        self.selected_window = window
        self.load_editor(window)
        self.refresh_active()
        self.show_editor_tab()
        self.show()
        self.raise_()
        self.activateWindow()

    def select_active(self):
        window = self.window_from_current_item()
        if window is not None:
            self.select_window(window)

    def close_active(self):
        window = self.window_from_current_item()
        if window is not None:
            if self.selected_window is window:
                self.selected_window = None
                self.load_editor(None)
                self.hide_editor_tab()
            window.close()

    def toggle_active_lock(self):
        window = self.window_from_current_item()
        if window is not None:
            window.toggle_lock()
            self.refresh_active()
            if self.selected_window is window:
                self.load_editor(window)

    def clear_overlay_selection(self):
        for window in state.WINDOWS:
            window.set_selected(False)

    def load_editor(self, window):
        self.loading_editor = True
        enabled = window is not None
        animated_types = {AssetType.GIF, AssetType.FRAME_ANIMATION, AssetType.SPRITE_STRIP, AssetType.SPRITESHEET}

        self.clear_overlay_selection()
        if enabled:
            window.set_selected(True)

        self.editor_name.setText(window.asset.name if enabled else "Double click an asset to edit it")
        self.editor_type.setText(f"Type: {window.asset_type}" if enabled else "")
        self.editor_placeholder.setVisible(not enabled)
        self.selected_group.setVisible(enabled)
        self.transform_group.setVisible(enabled)
        self.behavior_group.setVisible(enabled)
        self.scale_slider.setEnabled(enabled)
        self.opacity_slider.setEnabled(enabled)
        self.speed_row.setVisible(enabled and window.asset_type in animated_types)
        self.speed_slider.setEnabled(enabled and window.asset_type in animated_types)
        self.top_check.setEnabled(enabled)
        self.click_check.setEnabled(enabled)
        self.lock_check.setEnabled(enabled)
        self.reload_button.setEnabled(enabled)

        self.scale_slider.setValue(window.scale if enabled else 100)
        self.opacity_slider.setValue(window.opacity if enabled else 100)
        self.speed_slider.setValue(window.speed if enabled else 100)
        self.top_check.setChecked(window.always_on_top if enabled else False)
        self.click_check.setChecked(window.click_through if enabled else False)
        self.lock_check.setChecked(window.locked if enabled else False)
        self.scale_label.setText(f"Scale: {self.scale_slider.value()}%")
        self.opacity_label.setText(f"Opacity: {self.opacity_slider.value()}%")
        self.speed_label.setText(f"Speed: {self.speed_slider.value()}%")
        self.rebuild_runtime_editor(window if enabled else None)

        self.loading_editor = False

    def rebuild_runtime_editor(self, window):
        self.clear_layout(self.spritesheet_layout)
        self.clear_layout(self.composite_layout)
        self.layer_value_sliders = {}
        self.animation_combo = None
        self.spritesheet_group.hide()
        self.composite_group.hide()

        if window is None:
            return

        if window.asset_type == AssetType.COMPOSITE_UI:
            values = window.clipped_layer_values()
            if not values:
                return
            for name, value in values.items():
                display_name = self.display_layer_name(name)
                label = QLabel(f"{display_name}: {round(value * 100)}%")
                slider = QSlider(Qt.Horizontal)
                slider.setRange(0, 100)
                slider.setValue(round(value * 100))
                slider.valueChanged.connect(
                    lambda slider_value, layer=name, layer_label=label, name_text=display_name: self.editor_layer_value_changed(
                        layer, slider_value, layer_label, name_text
                    )
                )
                self.layer_value_sliders[name] = slider
                self.composite_layout.addWidget(self.slider_row(label, slider))
            self.composite_group.show()
            return

        if window.asset_type == AssetType.SPRITESHEET:
            animations = window.available_animations()
            if not animations:
                return
            self.animation_combo = QComboBox()
            self.animation_combo.addItems(animations)
            if window.current_animation in animations:
                self.animation_combo.setCurrentText(window.current_animation)
            self.animation_combo.currentTextChanged.connect(self.editor_animation_changed)
            self.spritesheet_layout.addWidget(QLabel("Animation"))
            self.spritesheet_layout.addWidget(self.animation_combo)
            self.spritesheet_group.show()
            return

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def display_layer_name(self, name):
        return str(name).replace("_", " ").strip().title() or "Layer"

    def editor_layer_value_changed(self, layer_name, slider_value, label, display_name):
        label.setText(f"{display_name}: {slider_value}%")
        if not self.loading_editor and self.selected_window in state.WINDOWS:
            try:
                self.selected_window.set_layer_value(layer_name, slider_value / 100)
            except Exception as exc:
                log_warning("Unable to update composite layer value %s: %s", layer_name, exc)

    def editor_animation_changed(self, animation_name):
        if not self.loading_editor and self.selected_window in state.WINDOWS:
            if not self.selected_window.set_animation(animation_name):
                log_warning("Unable to switch to animation: %s", animation_name)
                QMessageBox.warning(self, "Animation", f"Unable to switch to animation: {animation_name}")

    def reload_selected_asset(self):
        if self.selected_window not in state.WINDOWS:
            return
        asset = detect_asset(self.selected_window.asset_path)
        if asset is None:
            log_warning("Unable to reload selected asset definition: %s", self.selected_window.asset_path)
            QMessageBox.warning(self, "Reload Asset", "Unable to reload this asset definition.")
            return
        if not self.selected_window.reload_asset_definition(asset):
            log_warning("Reload failed for selected asset: %s", self.selected_window.asset_path)
            QMessageBox.warning(self, "Reload Asset", "Reload failed. The running overlay was kept unchanged.")
            return
        self.load_editor(self.selected_window)
        self.refresh_active()

    def editor_scale_changed(self, value):
        self.scale_label.setText(f"Scale: {value}%")
        if not self.loading_editor and self.selected_window in state.WINDOWS:
            self.selected_window.set_scale(value)

    def editor_opacity_changed(self, value):
        self.opacity_label.setText(f"Opacity: {value}%")
        if not self.loading_editor and self.selected_window in state.WINDOWS:
            self.selected_window.set_opacity_percent(value)

    def editor_speed_changed(self, value):
        self.speed_label.setText(f"Speed: {value}%")
        if not self.loading_editor and self.selected_window in state.WINDOWS:
            self.selected_window.set_speed(value)

    def editor_top_changed(self, checked):
        if not self.loading_editor and self.selected_window in state.WINDOWS:
            self.selected_window.always_on_top = checked
            self.selected_window.apply_window_flags()
            save_config()

    def editor_click_changed(self, checked):
        if not self.loading_editor and self.selected_window in state.WINDOWS:
            self.selected_window.click_through = checked
            self.selected_window.apply_click_through()
            save_config()

    def editor_lock_changed(self, checked):
        if not self.loading_editor and self.selected_window in state.WINDOWS:
            self.selected_window.locked = checked
            save_config()
            self.refresh_active()

    def closeEvent(self, event):
        self.clear_overlay_selection()
        if state.EXITING:
            super().closeEvent(event)
            return

        result = confirm_exit_or_tray(self)
        if result == "exit":
            event.accept()
            return

        event.ignore()
