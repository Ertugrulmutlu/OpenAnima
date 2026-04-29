from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from . import state
from .assets import asset_packs, gifs_for_pack, import_gif_to_assets, make_thumbnail, save_config
from .constants import BASE_DIR, THUMBNAIL_SIZE
from .overlay import add_window, confirm_exit_or_tray
from .startup import set_startup_enabled, startup_enabled


class ControlPanel(QWidget):
    def __init__(self, app_icon=None):
        super().__init__()
        self.selected_window = None
        self.loading_editor = False
        self.editor_tab = None
        self.editor_tab_index = -1
        self.tray_icon = None

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
        self.build_editor_tab()

        self.refresh_packs()
        self.refresh_active()
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
        subtitle = QLabel("Choose an asset pack and add GIFs to the desktop.")
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
        self.library_list.itemDoubleClicked.connect(lambda item: self.add_selected_library_gif())

        buttons = QHBoxLayout()
        import_button = QPushButton("Import GIF")
        add_button = QPushButton("Add to Desktop")
        import_button.clicked.connect(self.import_gif)
        add_button.clicked.connect(self.add_selected_library_gif)
        buttons.addWidget(import_button)
        buttons.addStretch()
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

        title = QLabel("Active Animations")
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
        close_button = QPushButton("Close Selected")
        lock_button = QPushButton("Lock/Unlock")
        hide_all_button = QPushButton("Hide all overlays")
        show_all_button = QPushButton("Show all overlays")

        select_button.clicked.connect(self.select_active)
        close_button.clicked.connect(self.close_active)
        lock_button.clicked.connect(self.toggle_active_lock)
        hide_all_button.clicked.connect(self.hide_all_overlays)
        show_all_button.clicked.connect(self.show_all_overlays)

        buttons.addWidget(select_button)
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

    def build_editor_tab(self):
        self.editor_tab = QWidget()
        layout = QVBoxLayout(self.editor_tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        title = QLabel("Editor")
        title.setObjectName("SectionTitle")
        self.editor_name = QLabel("Double click an animation to edit it")
        self.editor_name.setObjectName("SubtleLabel")

        controls = self.panel()
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(16, 16, 16, 16)
        controls_layout.setSpacing(14)

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

        self.top_check = QCheckBox("Always on top")
        self.click_check = QCheckBox("Click-through")
        self.top_check.toggled.connect(self.editor_top_changed)
        self.click_check.toggled.connect(self.editor_click_changed)

        controls_layout.addWidget(self.scale_label)
        controls_layout.addWidget(self.scale_slider)
        controls_layout.addWidget(self.opacity_label)
        controls_layout.addWidget(self.opacity_slider)
        controls_layout.addWidget(self.speed_label)
        controls_layout.addWidget(self.speed_slider)
        controls_layout.addSpacing(4)
        controls_layout.addWidget(self.top_check)
        controls_layout.addWidget(self.click_check)

        layout.addWidget(title)
        layout.addWidget(self.editor_name)
        layout.addWidget(controls)
        layout.addStretch()
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
        gif_paths = gifs_for_pack(self.active_pack_dir())
        if not gif_paths:
            item = QListWidgetItem("No GIFs yet. Click Import GIF to add your first animation.")
            item.setTextAlignment(Qt.AlignCenter)
            item.setFlags(Qt.NoItemFlags)
            self.library_list.addItem(item)
            return

        for path in gif_paths:
            item = QListWidgetItem(make_thumbnail(path), path.stem)
            item.setTextAlignment(Qt.AlignHCenter | Qt.AlignBottom)
            item.setData(Qt.UserRole, str(path))
            self.library_list.addItem(item)

    def refresh_active(self):
        selected_id = id(self.selected_window) if self.selected_window in state.WINDOWS else None
        self.active_list.clear()

        for window in state.WINDOWS:
            state_text = "locked" if window.locked else "unlocked"
            item = QListWidgetItem(make_thumbnail(window.gif_path), f"{window.gif_path.name}  -  {state_text}")
            item.setData(Qt.UserRole, id(window))
            self.active_list.addItem(item)
            if id(window) == selected_id:
                self.active_list.setCurrentItem(item)

        if self.selected_window not in state.WINDOWS:
            self.selected_window = None
            self.load_editor(None)
            self.hide_editor_tab()

    def window_from_current_item(self):
        item = self.active_list.currentItem()
        if item is None:
            return None
        window_id = item.data(Qt.UserRole)
        return next((window for window in state.WINDOWS if id(window) == window_id), None)

    def open_active_menu(self, pos):
        item = self.active_list.itemAt(pos)
        if item is None:
            return

        self.active_list.setCurrentItem(item)
        menu = QMenu(self)

        edit_action = QAction("Edit", self)
        edit_action.triggered.connect(self.select_active)
        menu.addAction(edit_action)

        close_action = QAction("Close animation", self)
        close_action.triggered.connect(self.close_active)
        menu.addAction(close_action)

        menu.exec(self.active_list.mapToGlobal(pos))

    def import_gif(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import GIF", str(BASE_DIR), "GIF files (*.gif)")
        if not path:
            return

        imported = import_gif_to_assets(path, self.active_pack_dir())
        if imported is None:
            return

        self.refresh_packs()
        for index in range(self.library_list.count()):
            item = self.library_list.item(index)
            if Path(item.data(Qt.UserRole)).resolve() == imported.resolve():
                self.library_list.setCurrentItem(item)
                break

    def add_selected_library_gif(self):
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

        self.clear_overlay_selection()
        if enabled:
            window.set_selected(True)

        self.editor_name.setText(window.gif_path.name if enabled else "Double click an animation to edit it")
        self.scale_slider.setEnabled(enabled)
        self.opacity_slider.setEnabled(enabled)
        self.speed_slider.setEnabled(enabled)
        self.top_check.setEnabled(enabled)
        self.click_check.setEnabled(enabled)

        self.scale_slider.setValue(window.scale if enabled else 100)
        self.opacity_slider.setValue(window.opacity if enabled else 100)
        self.speed_slider.setValue(window.speed if enabled else 100)
        self.top_check.setChecked(window.always_on_top if enabled else False)
        self.click_check.setChecked(window.click_through if enabled else False)
        self.scale_label.setText(f"Scale: {self.scale_slider.value()}%")
        self.opacity_label.setText(f"Opacity: {self.opacity_slider.value()}%")
        self.speed_label.setText(f"Speed: {self.speed_slider.value()}%")

        self.loading_editor = False

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
