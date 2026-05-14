from PySide6.QtCore import QSize


THUMBNAIL_SIZE = QSize(96, 96)


DARK_STYLE = """
QWidget {
    background-color: #191919;
    color: #ffffff;
    font-family: Segoe UI, Arial, sans-serif;
    font-size: 10pt;
}
QLabel {
    background-color: transparent;
}
QTabWidget::pane {
    border: 1px solid #333333;
    border-radius: 8px;
    background-color: #252525;
}
QTabBar::tab {
    background-color: #252525;
    color: #d8d8d8;
    padding: 9px 16px;
    border-top-left-radius: 7px;
    border-top-right-radius: 7px;
    margin-right: 3px;
}
QTabBar::tab:selected {
    background-color: #3a86ff;
    color: #ffffff;
}
QTabBar::tab:hover:!selected {
    background-color: #303030;
}
QPushButton {
    background-color: #2b2b2b;
    border: 1px solid #454545;
    border-radius: 7px;
    padding: 8px 12px;
    color: #ffffff;
    min-height: 18px;
    min-width: 72px;
}
QPushButton:hover {
    background-color: #363636;
    border-color: #3a86ff;
}
QPushButton#PrimaryButton {
    background-color: #345f9f;
    border-color: #3a86ff;
    font-weight: 600;
}
QPushButton#PrimaryButton:hover {
    background-color: #3f73bd;
}
QPushButton#DangerButton {
    border-color: #7f3838;
    color: #ffb4b4;
}
QPushButton#DangerButton:hover {
    background-color: #3a2424;
    border-color: #d65252;
}
QPushButton:pressed {
    background-color: #3a86ff;
}
QPushButton:disabled {
    color: #777777;
    background-color: #252525;
    border-color: #333333;
}
QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #252525;
    border: 1px solid #454545;
    border-radius: 7px;
    padding: 6px 9px;
    color: #ffffff;
    min-height: 18px;
}
QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {
    border-color: #3a86ff;
}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    width: 18px;
    border: 0;
}
QListWidget {
    background-color: #202020;
    border: 1px solid #303030;
    border-radius: 8px;
    padding: 8px;
    outline: 0;
}
QListWidget::item {
    border-radius: 8px;
    padding: 8px;
}
QListWidget::item:selected {
    background-color: #3a86ff;
    color: #ffffff;
}
QListWidget::item:hover:!selected {
    background-color: #303030;
}
QComboBox {
    background-color: #252525;
    border: 1px solid #454545;
    border-radius: 7px;
    padding: 7px 10px;
    color: #ffffff;
    min-height: 18px;
}
QComboBox:hover {
    border-color: #3a86ff;
}
QComboBox::drop-down {
    border: 0;
    width: 26px;
}
QComboBox QAbstractItemView {
    background-color: #252525;
    color: #ffffff;
    border: 1px solid #3a86ff;
    selection-background-color: #3a86ff;
}
QSlider::groove:horizontal {
    height: 6px;
    border-radius: 3px;
    background-color: #383838;
}
QSlider::sub-page:horizontal {
    background-color: #3a86ff;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background-color: #ffffff;
    border: 2px solid #3a86ff;
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}
QCheckBox {
    background-color: transparent;
    spacing: 8px;
}
QSlider {
    background-color: transparent;
}
QCheckBox::indicator {
    width: 17px;
    height: 17px;
    border-radius: 4px;
    border: 1px solid #555555;
    background-color: #252525;
}
QCheckBox::indicator:checked {
    background-color: #3a86ff;
    border-color: #3a86ff;
}
QLabel#SectionTitle {
    font-size: 14pt;
    font-weight: 600;
}
QLabel#SubtleLabel {
    color: #b8b8b8;
}
QLabel#AppTitle {
    font-size: 16pt;
    font-weight: 700;
    padding: 8px 8px 14px 8px;
}
QLabel#CardTitle {
    font-size: 11pt;
    font-weight: 600;
}
QLabel#EmptyTitle {
    font-size: 18pt;
    font-weight: 700;
}
QLabel#SavedLabel {
    color: #7bd88f;
    font-weight: 600;
}
QFrame#Panel {
    background-color: #252525;
    border: 1px solid #333333;
    border-radius: 8px;
}
QFrame#Sidebar, QFrame#InspectorPanel, QFrame#OverlayCard, QFrame#EmptyState {
    background-color: #222222;
    border: 1px solid #333333;
    border-radius: 8px;
}
QFrame#EmptyState {
    border-style: dashed;
}
QPushButton#NavButton {
    text-align: left;
    border: 0;
    background-color: transparent;
    padding: 10px 12px;
}
QPushButton#NavButton:hover {
    background-color: #2d2d2d;
}
QPushButton#NavButton:checked {
    background-color: #345f9f;
    color: #ffffff;
}
QGroupBox {
    border: 1px solid #343434;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
    background-color: #222222;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: #f0f0f0;
    font-weight: 600;
}
QScrollArea {
    border: 0;
}
QTextEdit {
    background-color: #202020;
    border: 1px solid #333333;
    border-radius: 8px;
    padding: 8px;
}
QWidget#EditorRow, QWidget#TransparentRow {
    background-color: transparent;
}
QListWidget#ActiveOverlayList::item {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 4px;
}
QListWidget#ActiveOverlayList::item:selected {
    background-color: transparent;
    border: 1px solid #3a86ff;
}
QListWidget#ActiveOverlayList::item:hover:!selected {
    background-color: #242424;
}
QScrollBar:vertical {
    background-color: #1f1f1f;
    width: 12px;
    margin: 2px;
    border-radius: 6px;
}
QScrollBar::handle:vertical {
    background-color: #4a4a4a;
    border-radius: 5px;
    min-height: 32px;
}
QScrollBar::handle:vertical:hover {
    background-color: #5a5a5a;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
    background: transparent;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}
QScrollBar:horizontal {
    background-color: #1f1f1f;
    height: 12px;
    margin: 2px;
    border-radius: 6px;
}
QScrollBar::handle:horizontal {
    background-color: #4a4a4a;
    border-radius: 5px;
    min-width: 32px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #5a5a5a;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
    background: transparent;
}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: transparent;
}
QMenu {
    background-color: #242424;
    color: #f2f2f2;
    border: 1px solid #3a3a3a;
    border-radius: 8px;
    padding: 6px;
}
QMenu::item {
    background-color: transparent;
    padding: 8px 28px 8px 12px;
    border-radius: 6px;
}
QMenu::item:selected {
    background-color: #345f9f;
    color: #ffffff;
}
QMenu::item:disabled {
    color: #777777;
}
QMenu::separator {
    height: 1px;
    background-color: #3a3a3a;
    margin: 6px 8px;
}
"""
