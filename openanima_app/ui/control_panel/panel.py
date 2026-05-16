from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QSize, Qt, QUrl
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ...overlay import confirm_exit_or_tray
from ...runtime import recovery, state
from ...runtime.logging import log_info, log_warning, recent_warnings_and_errors
from ...runtime.paths import APP_DATA_DIR, CONFIG_PATH, LOG_DIR, LOG_PATH
from ...runtime.session import persist_runtime_state, save_ui_state
from ...version import __version__
from . import desktop_page, editor_page, import_workflows, library_page, local_api_page, overlay_cards
from .about_page import build_about_page as build_about_page_widget
from .diagnostics_page import build_diagnostics_page
from .settings_page import build_settings_page as build_settings_page_widget


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=8):
        super().__init__(parent)
        self.items = []
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

    def addItem(self, item):
        self.items.append(item)

    def count(self):
        return len(self.items)

    def itemAt(self, index):
        return self.items[index] if 0 <= index < len(self.items) else None

    def takeAt(self, index):
        return self.items.pop(index) if 0 <= index < len(self.items) else None

    def expandingDirections(self):
        return Qt.Orientations()

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.do_layout(rect, test_only=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def do_layout(self, rect, test_only=False):
        margins = self.contentsMargins()
        effective = rect.adjusted(margins.left(), margins.top(), -margins.right(), -margins.bottom())
        x = effective.x()
        y = effective.y()
        line_height = 0

        for item in self.items:
            widget = item.widget()
            style = widget.style() if widget is not None else QApplication.style()
            spacing_x = self.spacing() + style.layoutSpacing(
                QSizePolicy.PushButton,
                QSizePolicy.PushButton,
                Qt.Horizontal,
            )
            spacing_y = self.spacing() + style.layoutSpacing(
                QSizePolicy.PushButton,
                QSizePolicy.PushButton,
                Qt.Vertical,
            )
            item_size = item.sizeHint()
            next_x = x + item_size.width() + spacing_x
            if next_x - spacing_x > effective.right() and line_height > 0:
                x = effective.x()
                y = y + line_height + spacing_y
                next_x = x + item_size.width() + spacing_x
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item_size))
            x = next_x
            line_height = max(line_height, item_size.height())

        return y + line_height - rect.y() + margins.bottom()


class ControlPanel(QWidget):
    def __init__(self, app_icon=None):
        super().__init__()
        self.selected_window = None
        self.loading_editor = False
        self.editor_tab = None
        self.tray_icon = None
        self.layer_value_sliders = {}
        self.nav_buttons = {}
        self._restoring_ui_state = True

        self.setWindowTitle("OpenAnima")
        if app_icon is not None and not app_icon.isNull():
            self.setWindowIcon(app_icon)
        self.setMinimumSize(720, 520)
        self.setAcceptDrops(True)
        self.inspector_stacked_below = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.sidebar = self.build_sidebar()
        self.sidebar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.pages = QStackedWidget()
        self.pages.setObjectName("MainPages")
        self.pages.setMinimumWidth(320)
        self.pages.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.inspector_shell = self.panel()
        self.inspector_shell.setObjectName("InspectorPanel")
        self.inspector_shell.setMinimumWidth(280)
        self.inspector_shell.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        inspector_layout = QVBoxLayout(self.inspector_shell)
        inspector_layout.setContentsMargins(0, 0, 0, 0)

        self.content_splitter = QSplitter(Qt.Horizontal)
        self.content_splitter.setChildrenCollapsible(False)
        self.content_splitter.addWidget(self.pages)
        self.content_splitter.addWidget(self.inspector_shell)
        self.content_splitter.setStretchFactor(0, 3)
        self.content_splitter.setStretchFactor(1, 1)
        self.content_splitter.setSizes([700, 340])

        layout.addWidget(self.sidebar)
        layout.addWidget(self.content_splitter, 1)

        self.build_library_tab()
        self.build_active_tab()
        self.build_settings_page()
        self.build_local_api_page()
        self.build_diagnostics_tab()
        self.build_about_page()
        self.build_editor_tab()
        inspector_layout.addWidget(self.editor_tab)
        self.select_page("Library")

        self.refresh_packs()
        self.refresh_active()
        self.refresh_diagnostics()
        self.load_editor(None)
        self.update_responsive_layout()
        self._restoring_ui_state = False

    def build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setMinimumWidth(132)
        sidebar.setMaximumWidth(176)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        title = QLabel("OpenAnima")
        title.setObjectName("AppTitle")
        layout.addWidget(title)

        for name in ("Library", "Desktop", "Settings", "Local API", "Diagnostics", "About"):
            button = QPushButton(name)
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, page=name: self.select_page(page))
            self.nav_buttons[name] = button
            layout.addWidget(button)

        layout.addStretch()
        return sidebar

    def add_page(self, name, widget):
        self.pages.addWidget(widget)
        widget.setProperty("pageName", name)

    def select_page(self, name):
        for index in range(self.pages.count()):
            widget = self.pages.widget(index)
            if widget.property("pageName") == name:
                self.pages.setCurrentIndex(index)
                break
        for page_name, button in self.nav_buttons.items():
            button.setChecked(page_name == name)
        self.update_inspector_visibility()
        if name == "Diagnostics":
            self.refresh_diagnostics()
        if name == "Local API":
            self.refresh_local_api_page()
        if not self._restoring_ui_state:
            save_ui_state(reason="control_panel_page_changed")

    def current_page_name(self):
        widget = self.pages.currentWidget()
        return widget.property("pageName") if widget is not None else None

    def update_inspector_visibility(self):
        if not hasattr(self, "inspector_shell"):
            return
        show_inspector = self.current_page_name() == "Desktop"
        self.inspector_shell.setVisible(show_inspector)
        self.update_responsive_layout()

    def restore_ui_state(self, ui):
        self._restoring_ui_state = True
        try:
            geometry = ui.get("control_panel_geometry") if isinstance(ui, dict) else None
            if isinstance(geometry, dict):
                self.setGeometry(
                    QRect(
                        int(geometry.get("x", self.x())),
                        int(geometry.get("y", self.y())),
                        int(geometry.get("width", self.width())),
                        int(geometry.get("height", self.height())),
                    )
                )
            last_page = ui.get("last_page") if isinstance(ui, dict) else None
            if isinstance(last_page, str):
                self.select_page(last_page)
        finally:
            self._restoring_ui_state = False

    def update_responsive_layout(self):
        narrow = self.width() < 980
        if narrow == self.inspector_stacked_below:
            return

        self.inspector_stacked_below = narrow
        self.content_splitter.setOrientation(Qt.Vertical if narrow else Qt.Horizontal)
        if narrow:
            self.inspector_shell.setMaximumWidth(16777215)
            self.inspector_shell.setMinimumWidth(0)
            self.inspector_shell.setMinimumHeight(220)
            self.content_splitter.setSizes([420, 260])
        else:
            self.inspector_shell.setMinimumWidth(280)
            self.inspector_shell.setMinimumHeight(0)
            self.content_splitter.setSizes([700, 340])

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_responsive_layout()
        self.update_library_grid()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._restoring_ui_state:
            save_ui_state(visible=True, reason="control_panel_shown")

    def hideEvent(self, event):
        super().hideEvent(event)
        if not self._restoring_ui_state and not state.EXITING:
            save_ui_state(visible=False, reason="control_panel_hidden")

    def update_library_grid(self):
        if not hasattr(self, "library_list") or not self.library_list.isVisible():
            return
        width = max(160, self.library_list.viewport().width())
        columns = max(1, width // 132)
        item_width = max(112, min(172, (width - 20) // columns))
        self.library_list.setGridSize(QSize(item_width, 150))

    def panel(self):
        frame = QFrame()
        frame.setObjectName("Panel")
        frame.setFrameShape(QFrame.NoFrame)
        return frame

    def prepare_button(self, button, minimum_width=96, tooltip=None):
        button.setMinimumWidth(minimum_width)
        button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        if tooltip:
            button.setToolTip(tooltip)
        return button

    def button_flow(self, *buttons):
        container = QWidget()
        container.setObjectName("TransparentRow")
        layout = FlowLayout(container, spacing=8)
        for button in buttons:
            layout.addWidget(button)
        return container

    def scroll_page(self, page):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(page)
        return scroll

    def build_library_tab(self):
        return library_page.build_library_tab(self)
    def build_active_tab(self):
        return desktop_page.build_active_tab(self)
    def build_settings_page(self):
        build_settings_page_widget(self)

    def build_local_api_page(self):
        local_api_page.build_local_api_page(self)

    def build_diagnostics_tab(self):
        build_diagnostics_page(self)

    def build_about_page(self):
        build_about_page_widget(self)

    def empty_state(self, title, message, actions):
        frame = self.panel()
        frame.setObjectName("EmptyState")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(12)
        title_label = QLabel(title)
        title_label.setObjectName("EmptyTitle")
        title_label.setAlignment(Qt.AlignCenter)
        message_label = QLabel(message)
        message_label.setObjectName("SubtleLabel")
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignCenter)
        button_row = None
        if actions:
            if len(actions) == 1:
                button_row = QHBoxLayout()
                button_row.addStretch()
            else:
                button_row = QVBoxLayout()
            button_row.setContentsMargins(0, 6, 0, 0)
            button_row.setSpacing(8)
            for label, handler in actions:
                button = QPushButton(label)
                if len(actions) == 1:
                    button.setObjectName("PrimaryButton")
                self.prepare_button(button, 160)
                button.clicked.connect(handler)
                button_row.addWidget(button, 0, Qt.AlignCenter)
            if len(actions) == 1:
                button_row.addStretch()
        layout.addStretch()
        layout.addWidget(title_label, 0, Qt.AlignCenter)
        if message:
            layout.addWidget(message_label, 0, Qt.AlignCenter)
        if button_row is not None:
            layout.addLayout(button_row)
        layout.addStretch()
        return frame

    def build_editor_tab(self):
        return editor_page.build_editor_tab(self)
    def slider_row(self, value_label, slider):
        return editor_page.slider_row(self, value_label, slider)
    def movement_spin(self, minimum, maximum, step):
        return editor_page.movement_spin(self, minimum, maximum, step)
    def show_editor_tab(self):
        self.select_page("Desktop")

    def hide_editor_tab(self):
        return

    def active_pack_dir(self):
        return library_page.active_pack_dir(self)
    def refresh_packs(self):
        return library_page.refresh_packs(self)
    def change_asset_root(self):
        path = QFileDialog.getExistingDirectory(self, "Change Assets Folder", str(state.ASSETS_DIR))
        if not path:
            return

        state.ASSETS_DIR = Path(path).resolve()
        state.ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        persist_runtime_state("asset_root_changed")
        self.refresh_packs()

    def refresh_library(self):
        return library_page.refresh_library(self)
    def refresh_active(self):
        return desktop_page.refresh_active(self)
    def refresh_local_api_page(self):
        return local_api_page.refresh_local_api_page(self)
    def local_api_enabled_changed(self, checked):
        return local_api_page.local_api_enabled_changed(self, checked)
    def regenerate_local_api_token(self):
        return local_api_page.regenerate_local_api_token(self)
    def copy_local_api_token(self):
        return local_api_page.copy_local_api_token(self)
    def copy_local_api_url(self):
        return local_api_page.copy_local_api_url(self)
    def test_local_api_status(self):
        return local_api_page.test_local_api_status(self)
    def open_local_api_docs(self):
        return local_api_page.open_local_api_docs(self)
    def overlay_card(self, window):
        return overlay_cards.overlay_card(self, window)
    def overlay_badges(self, window):
        return overlay_cards.overlay_badges(self, window)
    def toggle_overlay_visible(self, window):
        return desktop_page.toggle_overlay_visible(self, window)
    def run_overlay_action(self, window):
        return desktop_page.run_overlay_action(self, window)
    def close_window(self, window):
        return desktop_page.close_window(self, window)
    def refresh_diagnostics(self):
        if not hasattr(self, "diagnostics_recent"):
            return

        self.diagnostics_version.setText(f"Version: {__version__}")
        self.diagnostics_data_dir.setText(f"Data: {APP_DATA_DIR}")
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
                f"Data directory: {APP_DATA_DIR}",
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
        return desktop_page.window_from_current_item(self)
    def library_path_from_current_item(self):
        return library_page.library_path_from_current_item(self)
    def open_library_menu(self, pos):
        item = self.library_list.itemAt(pos)
        if item is None or not item.data(Qt.UserRole):
            return

        self.library_list.setCurrentItem(item)
        menu = QMenu(self)

        add_action = QAction("Add to Desktop", self)
        add_action.triggered.connect(self.add_selected_library_asset)
        menu.addAction(add_action)

        configure_action = QAction("Edit Asset Metadata", self)
        configure_action.triggered.connect(self.configure_selected_library_asset)
        menu.addAction(configure_action)

        menu.exec(self.library_list.mapToGlobal(pos))

    def open_active_menu(self, pos):
        item = self.active_list.itemAt(pos)
        if item is None:
            return

        self.active_list.setCurrentItem(item)
        menu = QMenu(self)

        edit_action = QAction("Edit Overlay", self)
        edit_action.triggered.connect(self.select_active)
        menu.addAction(edit_action)

        configure_action = QAction("Edit Asset Metadata", self)
        configure_action.triggered.connect(self.configure_active_asset)
        menu.addAction(configure_action)

        close_action = QAction("Remove Overlay", self)
        close_action.triggered.connect(self.close_active)
        menu.addAction(close_action)

        menu.exec(self.active_list.mapToGlobal(pos))

    def import_asset(self):
        return import_workflows.import_asset(self)
    def import_folder(self):
        return import_workflows.import_folder(self)
    def import_pack(self):
        return import_workflows.import_pack(self)
    def import_asset_pack_path(self, path):
        return import_workflows.import_asset_pack_path(self, path)
    def import_analyzed_path(self, path, add_to_desktop=False):
        return import_workflows.import_analyzed_path(self, path, add_to_desktop)
    def import_dropped_paths(self, paths):
        return import_workflows.import_dropped_paths(self, paths)
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dropEvent(self, event):
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self.import_dropped_paths(paths)
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    def create_import_from_setup(self, path, metadata, asset_name):
        return import_workflows.create_import_from_setup(self, path, metadata, asset_name)
    def select_imported_library_item(self, imported):
        imported = Path(imported).resolve()
        for index in range(self.library_list.count()):
            item = self.library_list.item(index)
            item_path = item.data(Qt.UserRole)
            if item_path and Path(item_path).resolve() == imported:
                self.library_list.setCurrentItem(item)
                break

    def configure_selected_library_asset(self):
        return import_workflows.configure_selected_library_asset(self)
    def configure_active_asset(self):
        return import_workflows.configure_active_asset(self)
    def configure_selected_overlay_asset(self):
        return import_workflows.configure_selected_overlay_asset(self)
    def configure_asset_path(self, path):
        return import_workflows.configure_asset_path(self, path)
    def save_asset_metadata(self, path, metadata, asset_name):
        return import_workflows.save_asset_metadata(self, path, metadata, asset_name)
    def offer_reload_running_overlays(self, asset_path):
        return import_workflows.offer_reload_running_overlays(self, asset_path)
    def add_selected_library_asset(self):
        return library_page.add_selected_library_asset(self)
    def hide_all_overlays(self):
        recovery.hide_all_overlays()
        self.refresh_active()

    def show_all_overlays(self):
        recovery.show_all_overlays()
        self.refresh_active()

    def bring_all_overlays_to_center(self):
        recovery.bring_all_overlays_to_center()
        self.refresh_active()

    def disable_click_through_for_all(self):
        recovery.disable_click_through_for_all()
        if self.selected_window in state.WINDOWS:
            self.load_editor(self.selected_window)
        self.refresh_active()

    def unlock_all_overlays(self):
        recovery.unlock_all_overlays()
        if self.selected_window in state.WINDOWS:
            self.load_editor(self.selected_window)
        self.refresh_active()

    def clear_saved_session(self):
        if not state.WINDOWS:
            state.PRESERVED_WINDOW_CONFIGS = []
            persist_runtime_state("clear_saved_session", [], force_empty=True)
            log_info("Recovery action: clear saved session requested with no active overlays")
            self.refresh_active()
            return

        result = QMessageBox.question(
            self,
            "Clear Saved Session",
            "Close all active overlays and save an empty session?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if result != QMessageBox.Yes:
            return

        self.selected_window = None
        self.load_editor(None)
        self.hide_editor_tab()
        recovery.clear_saved_session()
        self.refresh_active()

    def select_window(self, window):
        return desktop_page.select_window(self, window)
    def active_selection_changed(self):
        return desktop_page.active_selection_changed(self)
    def select_active(self):
        return desktop_page.select_active(self)
    def close_active(self):
        return desktop_page.close_active(self)
    def toggle_active_lock(self):
        return desktop_page.toggle_active_lock(self)
    def toggle_selected_lock(self):
        return desktop_page.toggle_selected_lock(self)
    def focus_selected_overlay(self):
        return desktop_page.focus_selected_overlay(self)
    def remove_selected_overlay(self):
        return desktop_page.remove_selected_overlay(self)
    def clear_overlay_selection(self):
        return desktop_page.clear_overlay_selection(self)
    def set_editor_signals_blocked(self, blocked):
        return editor_page.set_editor_signals_blocked(self, blocked)
    def load_editor(self, window):
        return editor_page.load_editor(self, window)
    def rebuild_runtime_editor(self, window):
        return editor_page.rebuild_runtime_editor(self, window)
    def clear_layout(self, layout):
        return editor_page.clear_layout(self, layout)
    def display_layer_name(self, name):
        return editor_page.display_layer_name(self, name)
    def mark_saved(self):
        return editor_page.mark_saved(self)
    def editor_layer_value_changed(self, layer_name, slider_value, label, display_name):
        return editor_page.editor_layer_value_changed(self, layer_name, slider_value, label, display_name)
    def editor_animation_changed(self, animation_name):
        return editor_page.editor_animation_changed(self, animation_name)
    def reload_selected_asset(self):
        return editor_page.reload_selected_asset(self)
    def editor_scale_changed(self, value):
        return editor_page.editor_scale_changed(self, value)
    def editor_opacity_changed(self, value):
        return editor_page.editor_opacity_changed(self, value)
    def editor_speed_changed(self, value):
        return editor_page.editor_speed_changed(self, value)
    def editor_top_changed(self, checked):
        return editor_page.editor_top_changed(self, checked)
    def editor_click_changed(self, checked):
        return editor_page.editor_click_changed(self, checked)
    def editor_visibility_changed(self, checked):
        return editor_page.editor_visibility_changed(self, checked)
    def editor_lock_changed(self, checked):
        return editor_page.editor_lock_changed(self, checked)
    def current_action_config(self):
        return editor_page.current_action_config(self)
    def editor_action_changed(self):
        return editor_page.editor_action_changed(self)
    def browse_action_target(self):
        return editor_page.browse_action_target(self)
    def test_selected_action(self):
        return editor_page.test_selected_action(self)
    def current_movement_config(self):
        return editor_page.current_movement_config(self)
    def editor_movement_changed(self):
        return editor_page.editor_movement_changed(self)
    def closeEvent(self, event):
        self.clear_overlay_selection()
        if state.EXITING:
            persist_runtime_state("control_panel_close_while_exiting", force=True)
            super().closeEvent(event)
            return

        result = confirm_exit_or_tray(self)
        if result == "exit":
            persist_runtime_state("control_panel_close_event", force=True)
            event.accept()
            return

        event.ignore()
