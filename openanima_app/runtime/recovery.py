from PySide6.QtCore import QPoint

from . import state
from .logging import log_info
from .session import persist_runtime_state


def show_all_overlays():
    for window in state.WINDOWS:
        if hasattr(window, "set_intended_visible"):
            window.set_intended_visible(True)
        else:
            window.setVisible(True)
        window.raise_()
    persist_runtime_state("recovery_show_all_overlays")
    log_info("Recovery action: show all overlays")


def hide_all_overlays():
    for window in state.WINDOWS:
        if hasattr(window, "set_intended_visible"):
            window.set_intended_visible(False)
        else:
            window.setVisible(False)
    persist_runtime_state("recovery_hide_all_overlays")
    log_info("Recovery action: hide all overlays")


def disable_click_through_for_all():
    changed = 0
    for window in state.WINDOWS:
        if window.click_through:
            changed += 1
        window.click_through = False
        window.apply_click_through()
    persist_runtime_state("recovery_disable_click_through")
    log_info("Recovery action: disabled click-through for %s overlays", changed)


def unlock_all_overlays():
    changed = 0
    for window in state.WINDOWS:
        if window.locked:
            changed += 1
        window.locked = False
    persist_runtime_state("recovery_unlock_all")
    log_info("Recovery action: unlocked %s overlays", changed)


def bring_all_overlays_to_center():
    for index, window in enumerate(state.WINDOWS):
        centered = window.centered_on_primary_screen()
        offset = 24 * index
        target = QPoint(centered.x() + offset, centered.y() + offset)
        window.move(window.clamped_position(target))
        if hasattr(window, "set_intended_visible"):
            window.set_intended_visible(True)
        else:
            window.setVisible(True)
        window.raise_()
    persist_runtime_state("recovery_bring_all_to_center")
    log_info("Recovery action: brought %s overlays to center", len(state.WINDOWS))


def clear_saved_session():
    windows = list(state.WINDOWS)
    state.PRESERVED_WINDOW_CONFIGS = []
    for window in windows:
        window.close()
    state.WINDOWS.clear()
    persist_runtime_state("clear_saved_session", [], force_empty=True)
    log_info("Recovery action: cleared saved session and closed %s overlays", len(windows))
