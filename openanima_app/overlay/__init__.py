from PySide6.QtWidgets import QApplication

from ..runtime import state
from ..runtime.logging import log_info


_WINDOW_EXPORTS = {
    "DEFAULT_VIDEO_SIZE",
    "OverlayWindow",
    "VideoAssetRenderer",
    "add_window",
    "confirm_exit_or_tray",
    "refresh_control_panel",
}


def exit_app(reason="normal_app_quit"):
    state.EXITING = True
    log_info("OpenAnima exit requested")
    globals()["persist_runtime_state"](reason, force=True)
    app = QApplication.instance()
    if app is not None:
        app.quit()


def persist_runtime_state(*args, **kwargs):
    from ..runtime.session import persist_runtime_state as runtime_persist_runtime_state

    return runtime_persist_runtime_state(*args, **kwargs)


def __getattr__(name):
    if name in _WINDOW_EXPORTS:
        from . import window

        return getattr(window, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | _WINDOW_EXPORTS)


__all__ = sorted(_WINDOW_EXPORTS | {"QApplication", "exit_app", "persist_runtime_state"})
