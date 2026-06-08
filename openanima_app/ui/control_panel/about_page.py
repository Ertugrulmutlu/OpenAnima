from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ...version import __version__


def build_about_page(panel):
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(12)

    title_text = QCoreApplication.translate("AboutPage", "About")
    title = QLabel(title_text)
    title.setObjectName("SectionTitle")
    
    subtitle_text = QCoreApplication.translate(
        "AboutPage", 
        "OpenAnima places local visual assets on your desktop as independent overlays."
    )
    subtitle = QLabel(subtitle_text)
    subtitle.setObjectName("SubtleLabel")
    subtitle.setWordWrap(True)

    info = panel.panel()
    info_layout = QVBoxLayout(info)
    info_layout.setContentsMargins(16, 16, 16, 16)
    info_layout.setSpacing(10)
    
    version_prefix = QCoreApplication.translate("AboutPage", "Version:")
    formats_text = QCoreApplication.translate(
        "AboutPage", 
        "Supported formats: GIF, PNG/APNG, WebM, static images, sprite strips, spritesheets, frame folders, and composite UI assets."
    )
    workflow_text = QCoreApplication.translate(
        "AboutPage", 
        "Basic workflow: import an asset, review the detected type, add it to the desktop, then select the overlay to edit it in the Inspector."
    )
    repo_text = f"{QCoreApplication.translate('AboutPage', 'Repository:')} https://github.com/Ertugrulmutlu/OpenAnima"

    lines = (
        f"{version_prefix} {__version__}",
        formats_text,
        workflow_text,
        repo_text,
    )

    for text in lines:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        info_layout.addWidget(label)

    layout.addWidget(title)
    layout.addWidget(subtitle)
    layout.addWidget(info)
    layout.addStretch()
    
    panel.add_page(title_text, panel.scroll_page(tab))
