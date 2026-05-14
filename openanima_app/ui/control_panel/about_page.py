from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ...version import __version__


def build_about_page(panel):
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(12)

    title = QLabel("About")
    title.setObjectName("SectionTitle")
    subtitle = QLabel("OpenAnima places local visual assets on your desktop as independent overlays.")
    subtitle.setObjectName("SubtleLabel")
    subtitle.setWordWrap(True)

    info = panel.panel()
    info_layout = QVBoxLayout(info)
    info_layout.setContentsMargins(16, 16, 16, 16)
    info_layout.setSpacing(10)
    for text in (
        f"Version: {__version__}",
        "Supported formats: GIF, PNG/APNG, WebM, static images, sprite strips, spritesheets, frame folders, and composite UI assets.",
        "Basic workflow: import an asset, review the detected type, add it to the desktop, then select the overlay to edit it in the Inspector.",
        "Repository: https://github.com/Ertugrulmutlu/OpenAnima",
    ):
        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        info_layout.addWidget(label)

    layout.addWidget(title)
    layout.addWidget(subtitle)
    layout.addWidget(info)
    layout.addStretch()
    panel.add_page("About", panel.scroll_page(tab))
