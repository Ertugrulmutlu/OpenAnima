from PySide6.QtCore import Qt, QSize, QCoreApplication
from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from ...runtime import state
from ...runtime.session import persist_runtime_state


def build_active_tab(panel):
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(12)

    title_text = QCoreApplication.translate("DesktopPage", "Desktop")
    title = QLabel(title_text)
    title.setObjectName("SectionTitle")
    
    subtitle_text = QCoreApplication.translate("DesktopPage", "Manage active overlays and select one to edit it in the Inspector.")
    subtitle = QLabel(subtitle_text)
    subtitle.setObjectName("SubtleLabel")
    subtitle.setWordWrap(True)

    panel.active_list = QListWidget()
    panel.active_list.setObjectName("ActiveOverlayList")
    panel.active_list.setIconSize(QSize(56, 56))
    panel.active_list.setSpacing(10)
    panel.active_list.setContextMenuPolicy(Qt.CustomContextMenu)
    panel.active_list.currentItemChanged.connect(lambda current, previous: panel.active_selection_changed())
    panel.active_list.itemDoubleClicked.connect(lambda item: panel.select_active())
    panel.active_list.customContextMenuRequested.connect(panel.open_active_menu)

    panel.active_header = QWidget()
    panel.active_header.setObjectName("TransparentRow")
    active_header_layout = QHBoxLayout(panel.active_header)
    active_header_layout.setContentsMargins(0, 0, 0, 0)
    active_header_layout.setSpacing(10)
    
    header_title = QCoreApplication.translate("DesktopPage", "Active overlays")
    active_label = QLabel(header_title)
    active_label.setObjectName("CardTitle")
    
    hide_all_text = QCoreApplication.translate("DesktopPage", "Hide All")
    show_all_text = QCoreApplication.translate("DesktopPage", "Show All")
    hide_all_button = QPushButton(hide_all_text)
    show_all_button = QPushButton(show_all_text)
    
    hide_tip = QCoreApplication.translate("DesktopPage", "Hide all overlays")
    show_tip = QCoreApplication.translate("DesktopPage", "Show all overlays")
    panel.prepare_button(hide_all_button, 86, hide_tip)
    panel.prepare_button(show_all_button, 86, show_tip)
    
    hide_all_button.clicked.connect(panel.hide_all_overlays)
    show_all_button.clicked.connect(panel.show_all_overlays)
    active_header_layout.addWidget(active_label)
    active_header_layout.addStretch()
    active_header_layout.addWidget(hide_all_button)
    active_header_layout.addWidget(show_all_button)

    empty_title = QCoreApplication.translate("DesktopPage", "No active overlays")
    action_text = QCoreApplication.translate("DesktopPage", "Add Asset to Desktop")
    
    panel.desktop_empty = panel.empty_state(
        empty_title,
        " ",
        [(action_text, lambda: panel.select_page("Library"))],
    )
    panel.desktop_empty.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    layout.addWidget(title)
    layout.addWidget(subtitle)
    layout.addWidget(panel.desktop_empty, 1)
    layout.addWidget(panel.active_header)
    layout.addWidget(panel.active_list, 1)
    
    panel.add_page(title_text, tab)
    tab.setProperty("pageName", "Desktop")


def refresh_active(panel):
    selected_id = id(panel.selected_window) if panel.selected_window in state.WINDOWS else None
    has_overlays = bool(state.WINDOWS)
    panel.active_list.blockSignals(True)
    panel.active_list.clear()
    panel.active_list.setVisible(has_overlays)
    if hasattr(panel, "active_header"):
        panel.active_header.setVisible(has_overlays)
    if hasattr(panel, "desktop_empty"):
        panel.desktop_empty.setVisible(not has_overlays)

    for window in state.WINDOWS:
        item = QListWidgetItem()
        item.setData(Qt.UserRole, id(window))
        item.setSizeHint(QSize(260, 118))
        panel.active_list.addItem(item)
        panel.active_list.setItemWidget(item, panel.overlay_card(window))
        if id(window) == selected_id:
            panel.active_list.setCurrentItem(item)
    panel.active_list.blockSignals(False)

    if panel.selected_window not in state.WINDOWS:
        panel.selected_window = None
        panel.load_editor(None)
        panel.hide_editor_tab()
    panel.refresh_diagnostics()



def window_from_current_item(panel):
    item = panel.active_list.currentItem()
    if item is None:
        return None
    window_id = item.data(Qt.UserRole)
    return next((window for window in state.WINDOWS if id(window) == window_id), None)



def toggle_overlay_visible(panel, window):
    if window not in state.WINDOWS:
        return
    intended_visible = getattr(window, "intended_visible", None)
    if intended_visible is None:
        intended_visible = window.isVisible()
    window.set_intended_visible(not bool(intended_visible))
    persist_runtime_state("overlay_visibility_changed")
    panel.refresh_active()



def run_overlay_action(panel, window):
    if window not in state.WINDOWS:
        return
    ok, message = window.run_action()
    if not ok:
        dialog_title = QCoreApplication.translate("DesktopPage", "Run Action")
        QMessageBox.warning(panel, dialog_title, message)


def close_window(panel, window):
    if window not in state.WINDOWS:
        return
    if panel.selected_window is window:
        panel.selected_window = None
        panel.load_editor(None)
    window.close()



def active_selection_changed(panel):
    window = panel.window_from_current_item()
    if window is not None and window is not panel.selected_window:
        panel.selected_window = window
        panel.load_editor(window)



def select_active(panel):
    window = panel.window_from_current_item()
    if window is not None:
        panel.select_window(window)



def close_active(panel):
    window = panel.window_from_current_item()
    if window is not None:
        if panel.selected_window is window:
            panel.selected_window = None
            panel.load_editor(None)
            panel.hide_editor_tab()
        window.close()



def toggle_active_lock(panel):
    window = panel.window_from_current_item()
    if window is not None:
        window.toggle_lock()
        panel.refresh_active()
        if panel.selected_window is window:
            panel.load_editor(window)



def toggle_selected_lock(panel):
    if panel.selected_window not in state.WINDOWS:
        return
    panel.selected_window.toggle_lock()
    panel.load_editor(panel.selected_window)
    panel.refresh_active()



def focus_selected_overlay(panel):
    if panel.selected_window in state.WINDOWS:
        panel.select_window(panel.selected_window)



def remove_selected_overlay(panel):
    if panel.selected_window not in state.WINDOWS:
        return
    panel.close_window(panel.selected_window)



def clear_overlay_selection(panel):
    for window in state.WINDOWS:
        window.set_selected(False)



def select_window(panel, window):
    if window not in state.WINDOWS:
        return

    panel.selected_window = window
    panel.load_editor(window)
    panel.refresh_active()
    panel.show_editor_tab()
    panel.show()
    panel.raise_()
    panel.activateWindow()

