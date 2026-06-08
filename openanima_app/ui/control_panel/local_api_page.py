import json
import urllib.error
import urllib.request

from PySide6.QtCore import Qt, QUrl, QCoreApplication
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QCheckBox, QGroupBox, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget

from ... import local_api
from ...runtime import state
from ...runtime.paths import BASE_DIR


def get_warning_text():
    return QCoreApplication.translate(
        "LocalApiPage", 
        "The Local API allows other local tools to control OpenAnima overlays. "
        "Keep it disabled unless you need automation."
    )


def build_local_api_page(panel):
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(12)

    title = QLabel(QCoreApplication.translate("LocalApiPage", "Local API"))
    title.setObjectName("SectionTitle")
    subtitle = QLabel(QCoreApplication.translate("LocalApiPage", "Enable a local-only automation API for controlling overlays."))
    subtitle.setObjectName("SubtleLabel")
    subtitle.setWordWrap(True)

    group = QGroupBox(QCoreApplication.translate("LocalApiPage", "Experimental Local API"))
    group_layout = QVBoxLayout(group)
    group_layout.setContentsMargins(14, 18, 14, 14)
    group_layout.setSpacing(10)

    panel.local_api_toggle = QCheckBox(QCoreApplication.translate("LocalApiPage", "Enable Local API"))
    panel.local_api_toggle.setChecked(bool(state.LOCAL_API_CONFIG.get("enabled", False)))
    panel.local_api_toggle.toggled.connect(panel.local_api_enabled_changed)

    panel.local_api_url_label = QLabel()
    panel.local_api_url_label.setObjectName("SubtleLabel")
    panel.local_api_url_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    panel.local_api_url_label.setWordWrap(True)

    panel.local_api_status_label = QLabel()
    panel.local_api_status_label.setObjectName("SubtleLabel")
    panel.local_api_status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    panel.local_api_status_label.setWordWrap(True)

    panel.local_api_token_label = QLabel()
    panel.local_api_token_label.setObjectName("SubtleLabel")
    panel.local_api_token_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    panel.local_api_token_label.setWordWrap(True)

    panel.local_api_test_result = QTextEdit()
    panel.local_api_test_result.setReadOnly(True)
    panel.local_api_test_result.setMinimumHeight(90)
    panel.local_api_test_result.setPlainText(
        QCoreApplication.translate("LocalApiPage", "Status test has not been run.")
    )

    panel.local_api_example_label = QLabel()
    panel.local_api_example_label.setObjectName("SubtleLabel")
    panel.local_api_example_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    panel.local_api_example_label.setWordWrap(True)

    copy_url_button = QPushButton(QCoreApplication.translate("LocalApiPage", "Copy Base URL"))
    copy_token_button = QPushButton(QCoreApplication.translate("LocalApiPage", "Copy API Token"))
    regenerate_button = QPushButton(QCoreApplication.translate("LocalApiPage", "Regenerate Token"))
    test_button = QPushButton(QCoreApplication.translate("LocalApiPage", "Test Status"))
    docs_button = QPushButton(QCoreApplication.translate("LocalApiPage", "Open README"))
    panel.prepare_button(copy_url_button, 124)
    panel.prepare_button(copy_token_button, 126)
    panel.prepare_button(regenerate_button, 132)
    panel.prepare_button(test_button, 104)
    panel.prepare_button(docs_button, 108)
    copy_url_button.clicked.connect(panel.copy_local_api_url)
    copy_token_button.clicked.connect(panel.copy_local_api_token)
    regenerate_button.clicked.connect(panel.regenerate_local_api_token)
    test_button.clicked.connect(panel.test_local_api_status)
    docs_button.clicked.connect(panel.open_local_api_docs)

    warning = QLabel(get_warning_text())
    warning.setObjectName("SubtleLabel")
    warning.setWordWrap(True)

    group_layout.addWidget(panel.local_api_toggle)
    group_layout.addWidget(panel.local_api_status_label)
    group_layout.addWidget(panel.local_api_url_label)
    group_layout.addWidget(panel.local_api_token_label)
    group_layout.addWidget(
        panel.button_flow(copy_url_button, copy_token_button, regenerate_button, test_button, docs_button)
    )
    group_layout.addWidget(panel.local_api_example_label)
    group_layout.addWidget(panel.local_api_test_result)
    group_layout.addWidget(warning)

    layout.addWidget(title)
    layout.addWidget(subtitle)
    layout.addWidget(group)
    layout.addStretch()

    panel.add_page("Local API", panel.scroll_page(tab))
    refresh_local_api_page(panel)


def refresh_local_api_page(panel):
    if not hasattr(panel, "local_api_url_label"):
        return

    enabled = bool(state.LOCAL_API_CONFIG.get("enabled", False))
    token = str(state.LOCAL_API_CONFIG.get("token") or "")
    url = local_api.local_api_url()
    
    status_text = (
        QCoreApplication.translate("LocalApiPage", "Enabled") 
        if enabled and state.LOCAL_API_SERVER is not None 
        else QCoreApplication.translate("LocalApiPage", "Disabled")
    )
    
    prefix_status = QCoreApplication.translate("LocalApiPage", "Status:")
    prefix_address = QCoreApplication.translate("LocalApiPage", "Bound address:")
    prefix_port = QCoreApplication.translate("LocalApiPage", "Port:")
    prefix_url = QCoreApplication.translate("LocalApiPage", "Base URL:")
    prefix_example = QCoreApplication.translate("LocalApiPage", "Example:")

    server = state.LOCAL_API_SERVER
    port = server.bound_port if server is not None else local_api.DEFAULT_LOCAL_API_PORT
    
    panel.local_api_status_label.setText(
        f"{prefix_status} {status_text}\n{prefix_address} {local_api.LOCAL_API_HOST}\n{prefix_port} {port}"
    )
    panel.local_api_url_label.setText(f"{prefix_url} {url}")
    
    if token:
        token_text = QCoreApplication.translate("LocalApiPage", "Token: generated; use Copy API Token")
    else:
        token_text = QCoreApplication.translate("LocalApiPage", "Token: not generated")
    panel.local_api_token_label.setText(token_text)
    
    panel.local_api_example_label.setText(f'{prefix_example} Invoke-RestMethod -Uri "{url}/api/status" -Method Get')
    panel.local_api_toggle.blockSignals(True)
    panel.local_api_toggle.setChecked(enabled)
    panel.local_api_toggle.blockSignals(False)


def local_api_enabled_changed(panel, checked):
    local_api.set_local_api_enabled(bool(checked))
    refresh_local_api_page(panel)


def regenerate_local_api_token(panel):
    local_api.regenerate_local_api_token()
    refresh_local_api_page(panel)


def copy_local_api_token(panel):
    token = str(state.LOCAL_API_CONFIG.get("token") or "")
    QApplication.clipboard().setText(token)


def copy_local_api_url(panel):
    QApplication.clipboard().setText(local_api.local_api_url())


def test_local_api_status(panel):
    prefix_failure = QCoreApplication.translate("LocalApiPage", "Failure:")
    prefix_success = QCoreApplication.translate("LocalApiPage", "Success:")

    if not state.LOCAL_API_SERVER:
        err_msg = QCoreApplication.translate("LocalApiPage", "Local API is disabled.")
        panel.local_api_test_result.setPlainText(f"{prefix_failure} {err_msg}")
        refresh_local_api_page(panel)
        return
        
    url = f"{local_api.local_api_url()}/api/status"
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            body = response.read().decode("utf-8")
            parsed = json.loads(body)
            panel.local_api_test_result.setPlainText(f"{prefix_success}\n" + json.dumps(parsed, indent=2))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        panel.local_api_test_result.setPlainText(f"{prefix_failure} {exc}")
    refresh_local_api_page(panel)


def open_local_api_docs(panel):
    readme_path = BASE_DIR / "README.md"
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(readme_path)))