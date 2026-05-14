from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu


def open_overlay_menu(window, pos, confirm_exit_or_tray):
    menu = QMenu(window)

    close_action = QAction("Close asset", window)
    close_action.triggered.connect(window.close)
    menu.addAction(close_action)

    lock_action = QAction("Unlock" if window.locked else "Lock", window)
    lock_action.triggered.connect(window.toggle_lock)
    menu.addAction(lock_action)

    top_action = QAction(
        "Disable always-on-top" if window.always_on_top else "Enable always-on-top",
        window,
    )
    top_action.triggered.connect(window.toggle_always_on_top)
    menu.addAction(top_action)

    click_action = QAction(
        "Disable Click-Through Mode" if window.click_through else "Enable Click-Through Mode",
        window,
    )
    click_action.triggered.connect(window.toggle_click_through)
    menu.addAction(click_action)

    scale_menu = menu.addMenu("Scale")
    for value in (50, 100, 150):
        scale_action = QAction(f"{value}%", window)
        scale_action.triggered.connect(lambda checked=False, scale=value: window.set_scale(scale))
        scale_menu.addAction(scale_action)

    menu.addSeparator()

    run_action = QAction("Run action", window)
    run_action.setEnabled(bool(window.action.get("enabled")))
    run_action.triggered.connect(window.show_action_result)
    menu.addAction(run_action)

    menu.addSeparator()

    import_action = QAction("Import Asset...", window)
    import_action.triggered.connect(window.add_asset)
    menu.addAction(import_action)

    exit_action = QAction("Exit", window)
    exit_action.triggered.connect(lambda: confirm_exit_or_tray(window))
    menu.addAction(exit_action)

    menu.exec(pos)
