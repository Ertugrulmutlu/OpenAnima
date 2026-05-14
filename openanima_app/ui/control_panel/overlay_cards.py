from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout

from ...assets.thumbnails import make_thumbnail


def overlay_card(panel, window):
    card = QFrame()
    card.setObjectName("OverlayCard")
    card.mousePressEvent = lambda event, current=window: panel.select_window(current)
    card.setMinimumHeight(104)
    card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
    layout = QHBoxLayout(card)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(14)

    preview = QLabel()
    preview.setMinimumSize(64, 64)
    preview.setMaximumSize(76, 76)
    preview.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    preview.setPixmap(make_thumbnail(window.asset).pixmap(QSize(68, 68)))
    preview.setAlignment(Qt.AlignCenter)

    details = QVBoxLayout()
    details.setSpacing(8)
    name = QLabel(window.asset.name)
    name.setObjectName("CardTitle")
    name.setWordWrap(True)
    badges = QLabel("  ".join(panel.overlay_badges(window)))
    badges.setObjectName("SubtleLabel")
    badges.setWordWrap(True)
    details.addWidget(name)
    details.addWidget(badges)
    details.addStretch()

    layout.addWidget(preview)
    layout.addLayout(details, 1)
    return card



def overlay_badges(panel, window):
    intended_visible = getattr(window, "intended_visible", None)
    if intended_visible is None:
        intended_visible = window.isVisible()
    return [
    str(window.asset_type).replace("_", " ").title(),
    "Visible" if bool(intended_visible) else "Hidden",
    "Locked" if window.locked else "Unlocked",
    ]

