import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QGroupBox, QLabel, QPushButton, QVBoxLayout, QWidget

from ...runtime.startup import set_startup_enabled, startup_enabled


def build_settings_page(panel):
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(12)

    title = QLabel("Settings")
    title.setObjectName("SectionTitle")
    subtitle = QLabel("Application preferences, asset location, and recovery actions.")
    subtitle.setObjectName("SubtleLabel")
    subtitle.setWordWrap(True)

    asset_group = QGroupBox("Assets")
    asset_layout = QVBoxLayout(asset_group)
    asset_layout.setContentsMargins(14, 18, 14, 14)
    asset_layout.setSpacing(8)
    panel.settings_asset_root_label = QLabel()
    panel.settings_asset_root_label.setObjectName("SubtleLabel")
    panel.settings_asset_root_label.setWordWrap(True)
    change_root_button = QPushButton("Change Assets Folder")
    change_root_button.clicked.connect(panel.change_asset_root)
    asset_layout.addWidget(panel.settings_asset_root_label)
    asset_layout.addWidget(change_root_button, 0, Qt.AlignLeft)

    app_group = QGroupBox("Startup")
    app_layout = QVBoxLayout(app_group)
    app_layout.setContentsMargins(14, 18, 14, 14)
    panel.startup_check = QCheckBox("Start on system boot")
    panel.startup_check.setEnabled(False)
    if hasattr(panel.startup_check, "setVisible"):
        panel.startup_check.setVisible(sys.platform == "win32")
        if sys.platform == "win32":
            panel.startup_check.setEnabled(True)
            panel.startup_check.setChecked(startup_enabled())
            panel.startup_check.toggled.connect(set_startup_enabled)
    app_layout.addWidget(panel.startup_check)

    recovery_group = QGroupBox("Recovery")
    recovery_layout = QVBoxLayout(recovery_group)
    recovery_layout.setContentsMargins(14, 18, 14, 14)
    recovery_layout.setSpacing(8)

    center_all_button = QPushButton("Center All")
    disable_click_button = QPushButton("Disable Click-Through Mode")
    unlock_all_button = QPushButton("Unlock All")
    panel.prepare_button(center_all_button, 96, "Bring all overlays to center")
    panel.prepare_button(disable_click_button, 172)
    panel.prepare_button(unlock_all_button, 96, "Unlock all overlays")
    center_all_button.clicked.connect(panel.bring_all_overlays_to_center)
    disable_click_button.clicked.connect(panel.disable_click_through_for_all)
    unlock_all_button.clicked.connect(panel.unlock_all_overlays)

    recovery_show_button = QPushButton("Show All")
    recovery_hide_button = QPushButton("Hide All")
    clear_session_button = QPushButton("Clear saved session")
    panel.prepare_button(recovery_show_button, 92, "Show all overlays")
    panel.prepare_button(recovery_hide_button, 92, "Hide all overlays")
    panel.prepare_button(clear_session_button, 140)
    recovery_show_button.clicked.connect(panel.show_all_overlays)
    recovery_hide_button.clicked.connect(panel.hide_all_overlays)
    clear_session_button.clicked.connect(panel.clear_saved_session)
    recovery_layout.addWidget(
        panel.button_flow(
            center_all_button,
            disable_click_button,
            unlock_all_button,
            recovery_show_button,
            recovery_hide_button,
            clear_session_button,
        )
    )

    layout.addWidget(title)
    layout.addWidget(subtitle)
    layout.addWidget(asset_group)
    layout.addWidget(app_group)
    layout.addWidget(recovery_group)
    layout.addStretch()
    panel.add_page("Settings", panel.scroll_page(tab))
