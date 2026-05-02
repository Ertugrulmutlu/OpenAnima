import sys
from pathlib import Path

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon

from . import state
from .assets import assets_for_pack, config_warning, import_gif_to_assets, load_config, resolved_path, save_config, seed_default_assets_dir
from .constants import DARK_STYLE, DEFAULT_GIF, ICON_PATH
from .control_panel import ControlPanel
from .logging_utils import configure_logging, log_info
from .overlay import add_window, exit_app, refresh_control_panel
from .recovery import bring_all_overlays_to_center, disable_click_through_for_all, show_all_overlays


def show_control_panel():
    if state.CONTROL_PANEL is not None:
        state.CONTROL_PANEL.show()
        state.CONTROL_PANEL.raise_()
        state.CONTROL_PANEL.activateWindow()


def load_app_icon():
    return QIcon(str(ICON_PATH)) if ICON_PATH.exists() else QIcon()


def run_tray_recovery_action(action):
    action()
    refresh_control_panel()


def create_tray_icon(app, app_icon):
    tray_icon = app_icon if not app_icon.isNull() else app.style().standardIcon(QStyle.SP_ComputerIcon)
    tray = QSystemTrayIcon(tray_icon, app)
    tray.setToolTip("OpenAnima")

    menu = QMenu()
    show_action = QAction("Show Control Panel", menu)
    show_overlays_action = QAction("Show all overlays", menu)
    disable_click_action = QAction("Disable click-through for all", menu)
    center_action = QAction("Bring all overlays to center", menu)
    exit_action = QAction("Exit", menu)
    show_action.triggered.connect(show_control_panel)
    show_overlays_action.triggered.connect(lambda: run_tray_recovery_action(show_all_overlays))
    disable_click_action.triggered.connect(lambda: run_tray_recovery_action(disable_click_through_for_all))
    center_action.triggered.connect(lambda: run_tray_recovery_action(bring_all_overlays_to_center))
    exit_action.triggered.connect(exit_app)
    menu.addAction(show_action)
    menu.addSeparator()
    menu.addAction(show_overlays_action)
    menu.addAction(disable_click_action)
    menu.addAction(center_action)
    menu.addSeparator()
    menu.addAction(exit_action)

    tray.setContextMenu(menu)
    tray.menu = menu
    tray.activated.connect(lambda reason: show_control_panel() if reason == QSystemTrayIcon.DoubleClick else None)
    tray.show()
    return tray


def main():
    configure_logging()
    log_info("OpenAnima startup")
    configs = load_config()
    seed_default_assets_dir()
    state.ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    if DEFAULT_GIF.exists():
        import_gif_to_assets(DEFAULT_GIF, reuse_existing=True)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_STYLE)
    app_icon = load_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)
    app.aboutToQuit.connect(save_config)

    state.CONTROL_PANEL = ControlPanel(app_icon)
    state.CONTROL_PANEL.show()
    state.CONTROL_PANEL.tray_icon = create_tray_icon(app, app_icon)
    state.TRAY_ICON = state.CONTROL_PANEL.tray_icon

    if len(sys.argv) > 1:
        paths = [Path(arg) for arg in sys.argv[1:]]
        for path in paths:
            if path.exists():
                add_window(path)
    else:
        for item in configs:
            if isinstance(item, str):
                path = resolved_path(item)
                config = {}
            elif isinstance(item, dict):
                path = resolved_path(item.get("path") or item.get("gif_path") or item.get("asset_path") or "")
                config = item
            else:
                continue
            if path.exists():
                add_window(path, config, save=False)
            else:
                config_warning(f"Saved asset missing, skipped: {path}")

        if not state.WINDOWS:
            assets = assets_for_pack(state.ASSETS_DIR)
            if assets:
                add_window(assets[0].path)

    refresh_control_panel()
    exit_code = app.exec()
    log_info("OpenAnima shutdown")
    sys.exit(exit_code)
