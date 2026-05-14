from PySide6.QtWidgets import QApplication, QMessageBox

from ..runtime import state
from ..runtime.action_runner import ActionRunner, normalized_action_config
from ..runtime.logging import log_info
from ..assets import persist_runtime_state


def refresh_control_panel():
    if state.CONTROL_PANEL is not None:
        state.CONTROL_PANEL.refresh_active()


def exit_app(reason="normal_app_quit"):
    state.EXITING = True
    log_info("OpenAnima exit requested")
    persist_runtime_state(reason, force=True)
    QApplication.instance().quit()


def confirm_exit_or_tray(parent=None):
    dialog = QMessageBox(parent)
    dialog.setWindowTitle("Exit OpenAnima")
    dialog.setText("Do you want to exit the application or minimize to tray?")

    minimize_button = dialog.addButton("Minimize to Tray", QMessageBox.ActionRole)
    exit_button = dialog.addButton("Exit", QMessageBox.DestructiveRole)
    cancel_button = dialog.addButton("Cancel", QMessageBox.RejectRole)
    cancel_button.hide()
    dialog.setDefaultButton(minimize_button)
    dialog.setEscapeButton(cancel_button)
    dialog.exec()

    clicked = dialog.clickedButton()
    if clicked == minimize_button:
        if state.CONTROL_PANEL is not None:
            state.CONTROL_PANEL.hide()
        return "tray"

    if clicked == exit_button:
        exit_app("overlay_context_exit")
        return "exit"

    if clicked == cancel_button:
        return "cancel"

    return "cancel"


def toggle_lock(window):
    window.locked = not window.locked
    persist_runtime_state("overlay_lock_changed")
    refresh_control_panel()


def toggle_always_on_top(window):
    window.always_on_top = not window.always_on_top
    window.apply_window_flags()
    persist_runtime_state("overlay_always_on_top_changed")
    refresh_control_panel()


def toggle_click_through(window):
    window.click_through = not window.click_through
    window.apply_click_through()
    persist_runtime_state("overlay_click_through_changed")
    refresh_control_panel()


def set_scale(window, value):
    window.scale = int(value)
    window.apply_scale()
    persist_runtime_state("overlay_scale_changed")


def set_opacity_percent(window, value):
    window.opacity = int(value)
    window.setWindowOpacity(window.opacity / 100)
    persist_runtime_state("overlay_opacity_changed")


def set_speed(window, value):
    window.speed = int(value)
    if window.movie is not None:
        window.movie.setSpeed(window.speed)
    if window.frame_player is not None:
        window.frame_player.set_speed(window.speed)
    if window.apng_player is not None:
        window.apng_player.set_speed(window.speed)
    if window.video_renderer is not None:
        window.video_renderer.set_speed(window.speed)
    if window.sprite_player is not None:
        window.sprite_player.set_speed(window.speed)
    persist_runtime_state("overlay_speed_changed")


def set_action(window, config):
    window.action = normalized_action_config(config)
    persist_runtime_state("action_changed")


def run_action(window):
    return ActionRunner.run(window.action)


def show_action_result(window):
    ok, message = run_action(window)
    if not ok:
        QMessageBox.warning(window, "Run Action", message)
