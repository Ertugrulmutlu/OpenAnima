import sys

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtWidgets import QApplication


def remove_native_border(window):
    if sys.platform != "win32":
        return

    try:
        import ctypes

        hwnd = int(window.winId())
        color_none = ctypes.c_uint(0xFFFFFFFE)
        corner_none = ctypes.c_int(1)

        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 34, ctypes.byref(color_none), ctypes.sizeof(color_none)
        )
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 33, ctypes.byref(corner_none), ctypes.sizeof(corner_none)
        )
    except Exception:
        pass


def apply_window_flags(window):
    was_visible = window.isVisible()
    pos = window.pos()
    flags = Qt.FramelessWindowHint | Qt.Tool | Qt.NoDropShadowWindowHint
    if window.always_on_top:
        flags |= Qt.WindowStaysOnTopHint
    window.setWindowFlags(flags)
    window.move(window.clamped_position(pos))
    window.apply_click_through()
    if was_visible:
        window.show()
        window.raise_()
    remove_native_border(window)


def apply_click_through(window):
    window.setAttribute(Qt.WA_TransparentForMouseEvents, window.click_through)
    window.update()


def available_geometry():
    screen = QApplication.primaryScreen()
    return screen.availableGeometry() if screen else None


def visible_screen_geometry():
    screens = QApplication.screens()
    if not screens:
        return None

    geometry = QRect()
    for screen in screens:
        geometry = geometry.united(screen.availableGeometry()) if geometry.isValid() else screen.availableGeometry()
    return geometry


def centered_on_primary_screen(window):
    geometry = window.available_geometry() if hasattr(window, "available_geometry") else available_geometry()
    if geometry is None:
        return QPoint(100, 100)

    return QPoint(
        geometry.left() + max(0, (geometry.width() - max(1, window.width())) // 2),
        geometry.top() + max(0, (geometry.height() - max(1, window.height())) // 2),
    )


def restored_position(window, pos):
    visible_geometry = window.visible_screen_geometry() if hasattr(window, "visible_screen_geometry") else visible_screen_geometry()
    if visible_geometry is None:
        return pos

    window_rect = QRect(pos, window.size())
    if not window_rect.intersects(visible_geometry):
        return clamped_position(window, centered_on_primary_screen(window))

    return clamped_position(window, pos)


def clamped_position(window, pos):
    geometry = window.available_geometry() if hasattr(window, "available_geometry") else available_geometry()
    if geometry is None:
        return pos

    max_x = max(geometry.left(), geometry.right() - max(1, window.width()) + 1)
    max_y = max(geometry.top(), geometry.bottom() - max(1, window.height()) + 1)
    x = min(max(pos.x(), geometry.left()), max_x)
    y = min(max(pos.y(), geometry.top()), max_y)
    return QPoint(x, y)
