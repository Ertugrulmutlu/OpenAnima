import sys
from pathlib import Path

from PySide6.QtCore import QSize


def resource_path(relative_path):
    if getattr(sys, "frozen", False):
        base_path = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base_path = Path(__file__).resolve().parent.parent

    return base_path / relative_path


if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

DEFAULT_ASSETS_DIR = BASE_DIR / "assets"
CONFIG_PATH = BASE_DIR / "config.json"
LOG_DIR = BASE_DIR / "logs"
LOG_PATH = LOG_DIR / "openanima.log"
DEFAULT_GIF = BASE_DIR / "overlay.gif"
ICON_PATH = resource_path("icon.ico")
THUMBNAIL_SIZE = QSize(96, 96)


DARK_STYLE = """
QWidget {
    background-color: #1e1e1e;
    color: #ffffff;
    font-family: Segoe UI, Arial, sans-serif;
    font-size: 10pt;
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
    background-color: #2d2d2d;
    border: 1px solid #454545;
    border-radius: 7px;
    padding: 8px 12px;
    color: #ffffff;
}
QPushButton:hover {
    background-color: #363636;
    border-color: #3a86ff;
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
    background-color: #252525;
    border: 1px solid #333333;
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
    spacing: 8px;
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
    font-size: 13pt;
    font-weight: 600;
}
QLabel#SubtleLabel {
    color: #b8b8b8;
}
QFrame#Panel {
    background-color: #252525;
    border: 1px solid #333333;
    border-radius: 8px;
}
"""
