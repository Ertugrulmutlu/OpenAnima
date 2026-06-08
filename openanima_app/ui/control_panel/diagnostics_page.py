from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtWidgets import QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget


def build_diagnostics_page(panel):
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(12)

    title = QLabel(QCoreApplication.translate("DiagnosticsPage", "Diagnostics"))
    title.setObjectName("SectionTitle")
    
    subtitle_text = QCoreApplication.translate("DiagnosticsPage", "Review runtime paths, active overlays, and recent warnings.")
    subtitle = QLabel(subtitle_text)
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

    warnings_text = QCoreApplication.translate("DiagnosticsPage", "Recent warnings/errors")
    warnings_label = QLabel(warnings_text)
    warnings_label.setObjectName("SubtleLabel")
    panel.diagnostics_recent = QTextEdit()
    panel.diagnostics_recent.setReadOnly(True)
    panel.diagnostics_recent.setMinimumHeight(160)

    btn_open_logs = QCoreApplication.translate("DiagnosticsPage", "Open Logs Folder")
    btn_copy = QCoreApplication.translate("DiagnosticsPage", "Copy Diagnostic Info")
    btn_refresh = QCoreApplication.translate("DiagnosticsPage", "Refresh")

    open_logs_button = QPushButton(btn_open_logs)
    copy_button = QPushButton(btn_copy)
    refresh_button = QPushButton(btn_refresh)
    
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
    
    page_title = QCoreApplication.translate("DiagnosticsPage", "Diagnostics")
    panel.add_page(page_title, panel.scroll_page(tab))
