from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu
from PySide6.QtCore import QCoreApplication


def open_overlay_menu(window, pos, confirm_exit_or_tray):
    menu = QMenu(window)

    close_action = QAction(QCoreApplication.translate("OverlayMenu", "Close asset"), window)
    close_action.triggered.connect(window.close)
    menu.addAction(close_action)

    lock_text = (
        QCoreApplication.translate("OverlayMenu", "Unlock")
        if window.locked
        else QCoreApplication.translate("OverlayMenu", "Lock")
    )
    lock_action = QAction(lock_text, window)
    lock_action.triggered.connect(window.toggle_lock)
    menu.addAction(lock_action)

    top_text = (
        QCoreApplication.translate("OverlayMenu", "Disable always-on-top")
        if window.always_on_top
        else QCoreApplication.translate("OverlayMenu", "Enable always-on-top")
    )
    top_action = QAction(top_text, window)
    top_action.triggered.connect(window.toggle_always_on_top)
    menu.addAction(top_action)

    click_text = (
        QCoreApplication.translate("OverlayMenu", "Disable Click-Through Mode")
        if window.click_through
        else QCoreApplication.translate("OverlayMenu", "Enable Click-Through Mode")
    )
    click_action = QAction(click_text, window)
    click_action.triggered.connect(window.toggle_click_through)
    menu.addAction(click_action)

    scale_menu = menu.addMenu(QCoreApplication.translate("OverlayMenu", "Scale"))
    for value in (50, 100, 150):
        scale_action = QAction(f"{value}%", window)
        scale_action.triggered.connect(lambda checked=False, scale=value: window.set_scale(scale))
        scale_menu.addAction(scale_action)

    menu.addSeparator()

    run_action = QAction(QCoreApplication.translate("OverlayMenu", "Run action"), window)
    run_action.setEnabled(bool(window.action.get("enabled")))
    run_action.triggered.connect(window.show_action_result)
    menu.addAction(run_action)

    menu.addSeparator()

    import_action = QAction(QCoreApplication.translate("OverlayMenu", "Import Asset..."), window)
    import_action.triggered.connect(window.add_asset)
    menu.addAction(import_action)

    exit_action = QAction(QCoreApplication.translate("OverlayMenu", "Exit"), window)
    exit_action.triggered.connect(lambda: confirm_exit_or_tray(window))
    menu.addAction(exit_action)

    menu.exec(pos)
