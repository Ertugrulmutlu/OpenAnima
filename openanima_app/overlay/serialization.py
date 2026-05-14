from ..runtime.session import serialize_overlay_window


def to_config(window):
    return serialize_overlay_window(window)
