from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QListView, QListWidget,
    QListWidgetItem, QPushButton, QVBoxLayout, QWidget,
)

from ...assets.scanner import assets_for_pack, asset_packs
from ...assets.thumbnails import make_thumbnail
from ...overlay import add_window
from ...runtime import state
from ...ui.styles import THUMBNAIL_SIZE


def build_library_tab(panel):
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
    subtitle.setWordWrap(True)
    title_box.addWidget(title)
    title_box.addWidget(subtitle)

    panel.pack_combo = QComboBox()
    panel.pack_combo.currentIndexChanged.connect(panel.refresh_library)

    header.addLayout(title_box, 1)
    header.addWidget(QLabel("Pack"))
    header.addWidget(panel.pack_combo)

    root_row = QHBoxLayout()
    panel.asset_root_label = QLabel()
    panel.asset_root_label.setObjectName("SubtleLabel")
    panel.asset_root_label.setWordWrap(True)
    change_root_button = QPushButton("Change Assets Folder")
    change_root_button.clicked.connect(panel.change_asset_root)
    root_row.addWidget(panel.asset_root_label, 1)
    root_row.addWidget(change_root_button)

    panel.library_list = QListWidget()
    panel.library_list.setViewMode(QListView.IconMode)
    panel.library_list.setMovement(QListView.Static)
    panel.library_list.setResizeMode(QListView.Adjust)
    panel.library_list.setIconSize(THUMBNAIL_SIZE)
    panel.library_list.setGridSize(QSize(132, 150))
    panel.library_list.setSpacing(8)
    panel.library_list.setUniformItemSizes(True)
    panel.library_list.setContextMenuPolicy(Qt.CustomContextMenu)
    panel.library_list.itemDoubleClicked.connect(lambda item: panel.add_selected_library_asset())
    panel.library_list.customContextMenuRequested.connect(panel.open_library_menu)

    import_button = QPushButton("Import Asset")
    import_folder_button = QPushButton("Import Asset Folder")
    import_pack_button = QPushButton("Import Asset Pack")
    configure_button = QPushButton("Asset Metadata")
    add_button = QPushButton("Add to Desktop")
    panel.prepare_button(import_button, 104)
    panel.prepare_button(import_folder_button, 136)
    panel.prepare_button(import_pack_button, 124)
    panel.prepare_button(configure_button, 118, "Edit Asset Metadata")
    panel.prepare_button(add_button, 116)
    import_button.clicked.connect(panel.import_asset)
    import_folder_button.clicked.connect(panel.import_folder)
    import_pack_button.clicked.connect(panel.import_pack)
    configure_button.clicked.connect(panel.configure_selected_library_asset)
    add_button.clicked.connect(panel.add_selected_library_asset)
    buttons = panel.button_flow(import_button, import_folder_button, import_pack_button, configure_button, add_button)

    layout.addLayout(header)
    layout.addLayout(root_row)
    layout.addWidget(panel.library_list, 1)
    layout.addWidget(buttons)
    panel.library_empty = panel.empty_state(
        "No assets yet",
        "",
        [("Import Asset", panel.import_asset), ("Import Asset Pack", panel.import_pack)],
    )
    panel.library_empty.hide()
    layout.addWidget(panel.library_empty)
    panel.add_page("Library", tab)



def active_pack_dir(panel):
    return Path(panel.pack_combo.currentData() or state.ASSETS_DIR)



def refresh_packs(panel):
    current = panel.pack_combo.currentData()
    panel.pack_combo.blockSignals(True)
    panel.pack_combo.clear()

    for name, path in asset_packs():
        panel.pack_combo.addItem(name, str(path))

    if current:
        index = panel.pack_combo.findData(current)
        if index >= 0:
            panel.pack_combo.setCurrentIndex(index)

    panel.pack_combo.blockSignals(False)
    panel.asset_root_label.setText(f"Assets: {state.ASSETS_DIR}")
    if hasattr(panel, "settings_asset_root_label"):
        panel.settings_asset_root_label.setText(str(state.ASSETS_DIR))
    panel.refresh_library()



def refresh_library(panel):
    if not hasattr(panel, "library_list"):
        return

    panel.library_list.clear()
    assets = assets_for_pack(panel.active_pack_dir())
    if not assets:
        panel.library_list.hide()
        panel.library_empty.show()
        return

    panel.library_empty.hide()
    panel.library_list.show()
    panel.update_library_grid()
    for asset in assets:
        item = QListWidgetItem(make_thumbnail(asset), asset.name)
        item.setTextAlignment(Qt.AlignHCenter | Qt.AlignBottom)
        item.setData(Qt.UserRole, str(asset.path))
        panel.library_list.addItem(item)



def library_path_from_current_item(panel):
    item = panel.library_list.currentItem()
    if item is None or not item.data(Qt.UserRole):
        return None
    return Path(item.data(Qt.UserRole))



def add_selected_library_asset(panel):
    item = panel.library_list.currentItem()
    if item is not None and item.data(Qt.UserRole):
        add_window(item.data(Qt.UserRole))

