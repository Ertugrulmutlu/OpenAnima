from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget


def build_diagnostics_page(panel):
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(12)

    title = QLabel("Diagnostics")
    title.setObjectName("SectionTitle")
    subtitle = QLabel("Review runtime paths, active overlays, and recent warnings.")
    subtitle.setObjectName("SubtleLabel")
    subtitle.setWordWrap(True)

    info_panel = panel.panel()
    info_layout = QVBoxLayout(info_panel)
    info_layout.setContentsMargins(14, 14, 14, 14)
    info_layout.setSpacing(8)

    panel.diagnostics_version = QLabel()
    panel.diagnostics_data_dir = QLabel()
    panel.diagnostics_config_path = QLabel()
    panel.diagnostics_asset_root = QLabel()
    panel.diagnostics_log_path = QLabel()
    panel.diagnostics_overlay_count = QLabel()
    for label in (
        panel.diagnostics_version,
        panel.diagnostics_data_dir,
        panel.diagnostics_config_path,
        panel.diagnostics_asset_root,
        panel.diagnostics_log_path,
        panel.diagnostics_overlay_count,
    ):
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setWordWrap(True)
        info_layout.addWidget(label)

    warnings_label = QLabel("Recent warnings/errors")
    warnings_label.setObjectName("SubtleLabel")
    panel.diagnostics_recent = QTextEdit()
    panel.diagnostics_recent.setReadOnly(True)
    panel.diagnostics_recent.setMinimumHeight(160)

    open_logs_button = QPushButton("Open Logs Folder")
    copy_button = QPushButton("Copy Diagnostic Info")
    refresh_button = QPushButton("Refresh")
    panel.prepare_button(open_logs_button, 124)
    panel.prepare_button(copy_button, 140)
    panel.prepare_button(refresh_button, 92)
    open_logs_button.clicked.connect(panel.open_logs_folder)
    copy_button.clicked.connect(panel.copy_diagnostics)
    refresh_button.clicked.connect(panel.refresh_diagnostics)
    buttons = panel.button_flow(open_logs_button, copy_button, refresh_button)

    layout.addWidget(title)
    layout.addWidget(subtitle)
    layout.addWidget(info_panel)
    layout.addWidget(warnings_label)
    layout.addWidget(panel.diagnostics_recent, 1)
    layout.addWidget(buttons)
    panel.add_page("Diagnostics", panel.scroll_page(tab))
