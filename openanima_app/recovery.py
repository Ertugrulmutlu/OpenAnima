from PySide6.QtCore import QPoint

from . import state
from .assets import save_config
from .logging_utils import log_info


def show_all_overlays():
    for window in state.WINDOWS:
        window.setVisible(True)
        window.raise_()
    log_info("Recovery action: show all overlays")


def hide_all_overlays():
    for window in state.WINDOWS:
        window.setVisible(False)
    log_info("Recovery action: hide all overlays")


def disable_click_through_for_all():
    changed = 0
    for window in state.WINDOWS:
        if window.click_through:
            changed += 1
        window.click_through = False
        window.apply_click_through()
    save_config()
    log_info("Recovery action: disabled click-through for %s overlays", changed)


def unlock_all_overlays():
    changed = 0
    for window in state.WINDOWS:
        if window.locked:
            changed += 1
        window.locked = False
    save_config()
    log_info("Recovery action: unlocked %s overlays", changed)


def bring_all_overlays_to_center():
    for index, window in enumerate(state.WINDOWS):
        centered = window.centered_on_primary_screen()
        offset = 24 * index
        target = QPoint(centered.x() + offset, centered.y() + offset)
        window.move(window.clamped_position(target))
        window.setVisible(True)
        window.raise_()
    save_config()
    log_info("Recovery action: brought %s overlays to center", len(state.WINDOWS))


def clear_saved_session():
    windows = list(state.WINDOWS)
    for window in windows:
        window.close()
    state.WINDOWS.clear()
    save_config([])
    log_info("Recovery action: cleared saved session and closed %s overlays", len(windows))
