import json
import urllib.error
import urllib.request

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QCheckBox, QGroupBox, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget

from ... import local_api
from ...runtime import state
from ...runtime.paths import BASE_DIR


WARNING_TEXT = (
    "The Local API allows other local tools to control OpenAnima overlays. "
    "Keep it disabled unless you need automation."
)


def build_local_api_page(panel):
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(12)

    title = QLabel("Local API")
    title.setObjectName("SectionTitle")
    subtitle = QLabel("Enable a local-only automation API for controlling overlays.")
    subtitle.setObjectName("SubtleLabel")
    subtitle.setWordWrap(True)

    group = QGroupBox("Experimental Local API")
    group_layout = QVBoxLayout(group)
    group_layout.setContentsMargins(14, 18, 14, 14)
    group_layout.setSpacing(10)

    panel.local_api_toggle = QCheckBox("Enable Local API")
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
    panel.local_api_test_result.setPlainText("Status test has not been run.")

    panel.local_api_example_label = QLabel()
    panel.local_api_example_label.setObjectName("SubtleLabel")
    panel.local_api_example_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    panel.local_api_example_label.setWordWrap(True)

    copy_url_button = QPushButton("Copy Base URL")
    copy_token_button = QPushButton("Copy API Token")
    regenerate_button = QPushButton("Regenerate Token")
    test_button = QPushButton("Test Status")
    docs_button = QPushButton("Open README")
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

    warning = QLabel(WARNING_TEXT)
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
    status = "Enabled" if enabled and state.LOCAL_API_SERVER is not None else "Disabled"
    server = state.LOCAL_API_SERVER
    port = server.bound_port if server is not None else local_api.DEFAULT_LOCAL_API_PORT
    panel.local_api_status_label.setText(
        f"Status: {status}\nBound address: {local_api.LOCAL_API_HOST}\nPort: {port}"
    )
    panel.local_api_url_label.setText(f"Base URL: {url}")
    panel.local_api_token_label.setText("Token: generated; use Copy API Token" if token else "Token: not generated")
    panel.local_api_example_label.setText(f'Example: Invoke-RestMethod -Uri "{url}/api/status" -Method Get')
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
    if not state.LOCAL_API_SERVER:
        panel.local_api_test_result.setPlainText("Failure: Local API is disabled.")
        refresh_local_api_page(panel)
        return
    url = f"{local_api.local_api_url()}/api/status"
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            body = response.read().decode("utf-8")
            parsed = json.loads(body)
            panel.local_api_test_result.setPlainText("Success:\n" + json.dumps(parsed, indent=2))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        panel.local_api_test_result.setPlainText(f"Failure: {exc}")
    refresh_local_api_page(panel)


def open_local_api_docs(panel):
    readme_path = BASE_DIR / "README.md"
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(readme_path)))
