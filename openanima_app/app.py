import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon

from .assets.importer import import_gif_to_assets, seed_default_assets_dir
from .assets.paths import resolve_saved_asset_path
from .assets.scanner import assets_for_pack
from .overlay import add_window, exit_app, refresh_control_panel
from .runtime import state
from .runtime.config import config_warning, load_config_data
from .runtime.logging import configure_logging, log_info, log_warning
from .runtime.paths import DEFAULT_GIF, ICON_PATH
from .runtime.recovery import bring_all_overlays_to_center, disable_click_through_for_all, show_all_overlays
from .runtime.session import persist_runtime_state
from .ui.control_panel.panel import ControlPanel
from .ui.styles import DARK_STYLE


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


def tray_exit():
    exit_app("tray_exit")


def save_on_about_to_quit():
    if state.EXITING:
        return
    persist_runtime_state("app_about_to_quit", force=True)


def create_tray_icon(app, app_icon):
    tray_icon = app_icon if not app_icon.isNull() else app.style().standardIcon(QStyle.SP_ComputerIcon)
    tray = QSystemTrayIcon(tray_icon, app)
    tray.setToolTip("OpenAnima")

    menu = QMenu()
    show_action = QAction("Show Control Panel", menu)
    show_overlays_action = QAction("Show all overlays", menu)
    disable_click_action = QAction("Disable Click-Through Mode for all", menu)
    center_action = QAction("Bring all overlays to center", menu)
    exit_action = QAction("Exit", menu)
    show_action.triggered.connect(show_control_panel)
    show_overlays_action.triggered.connect(lambda: run_tray_recovery_action(show_all_overlays))
    disable_click_action.triggered.connect(lambda: run_tray_recovery_action(disable_click_through_for_all))
    center_action.triggered.connect(lambda: run_tray_recovery_action(bring_all_overlays_to_center))
    exit_action.triggered.connect(tray_exit)
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


def restore_saved_windows(configs, asset_root=None):
    restored = 0
    failed = []

    for item in configs:
        path_value = item.get("path") or item.get("gif_path") or item.get("asset_path") if isinstance(item, dict) else item
        config = item if isinstance(item, dict) else {}
        path = resolve_saved_asset_path(path_value, asset_root=asset_root)
        if path.exists():
            window = add_window(path, config, save=False)
            if window is not None:
                restored += 1
                continue

        failed.append(config if isinstance(config, dict) and config else {"path": str(path_value or "")})
        config_warning(f"Saved overlay could not be restored, preserving session entry: {path}")

    state.PRESERVED_WINDOW_CONFIGS = failed
    if restored:
        log_info("Restored %s saved overlay(s)", restored)
    if failed:
        log_warning("Preserved %s saved overlay config(s) after restore failure", len(failed))
    return restored, failed


def retry_restore_saved_windows(configs, asset_root=None):
    if not configs or state.WINDOWS:
        return

    restored, failed = restore_saved_windows(configs, asset_root=asset_root)
    if restored:
        state.PRESERVED_WINDOW_CONFIGS = failed
        refresh_control_panel()
        if state.CONTROL_PANEL is not None:
            state.CONTROL_PANEL.select_page("Desktop")
        persist_runtime_state("retry_restore_complete")


def apply_control_panel_startup_state(ui_config):
    if state.CONTROL_PANEL is None:
        return

    ui_config = ui_config if isinstance(ui_config, dict) else {}
    state.CONTROL_PANEL.restore_ui_state(ui_config)
    if ui_config.get("control_panel_visible", True) is False:
        state.CONTROL_PANEL.hide()
    else:
        show_control_panel()


def main():
    configure_logging()
    log_info("OpenAnima startup")
    state.RESTORING_SESSION = True
    config_data = load_config_data()
    configs = config_data["windows"]
    ui_config = config_data["ui"]
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
    app.aboutToQuit.connect(save_on_about_to_quit)

    state.CONTROL_PANEL = ControlPanel(app_icon)

    explicit_windows = 0
    for arg in sys.argv[1:]:
        path = Path(arg)
        if path.exists():
            window = add_window(path, save=False)
            if window is not None:
                explicit_windows += 1
        else:
            log_warning("Startup argument did not exist and was ignored: %s", arg)

    if explicit_windows == 0:
        restored, failed = restore_saved_windows(configs, asset_root=state.ASSETS_DIR)
        if restored and state.CONTROL_PANEL is not None:
            state.CONTROL_PANEL.select_page("Desktop")
        if failed:
            QTimer.singleShot(3000, lambda: retry_restore_saved_windows(configs, asset_root=state.ASSETS_DIR))

        if not configs and not state.WINDOWS:
            assets = assets_for_pack(state.ASSETS_DIR)
            if assets:
                add_window(assets[0].path, save=False)

    refresh_control_panel()
    state.CONTROL_PANEL.tray_icon = create_tray_icon(app, app_icon)
    state.TRAY_ICON = state.CONTROL_PANEL.tray_icon
    apply_control_panel_startup_state(ui_config)
    state.RESTORING_SESSION = False
    persist_runtime_state("startup_restore_complete", force=True)
    exit_code = app.exec()
    log_info("OpenAnima shutdown")
    sys.exit(exit_code)
