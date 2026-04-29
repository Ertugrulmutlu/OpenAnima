import sys
from pathlib import Path

from PySide6.QtCore import QPoint, QSize, Qt
from PySide6.QtGui import QAction, QImageReader, QMovie, QPainter
from PySide6.QtWidgets import QApplication, QFileDialog, QMenu, QMessageBox, QWidget

from .assets import import_gif_to_assets, save_config, stored_path
from .constants import BASE_DIR
from . import state


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


def refresh_control_panel():
    if state.CONTROL_PANEL is not None:
        state.CONTROL_PANEL.refresh_active()


def exit_app():
    state.EXITING = True
    save_config()
    QApplication.instance().quit()


def confirm_exit_or_tray(parent=None):
    dialog = QMessageBox(parent)
    dialog.setWindowTitle("Exit OpenAnima")
    dialog.setText("Do you want to exit the application or minimize to tray?")

    minimize_button = dialog.addButton("Minimize to Tray", QMessageBox.ActionRole)
    exit_button = dialog.addButton("Exit", QMessageBox.DestructiveRole)
    cancel_button = dialog.addButton("Cancel", QMessageBox.RejectRole)
    dialog.setDefaultButton(minimize_button)
    dialog.exec()

    clicked = dialog.clickedButton()
    if clicked == minimize_button:
        if state.CONTROL_PANEL is not None:
            state.CONTROL_PANEL.hide()
        return "tray"

    if clicked == exit_button:
        exit_app()
        return "exit"

    if clicked == cancel_button:
        return "cancel"

    return "cancel"


def add_window(gif_path, config=None, save=True):
    asset_path = import_gif_to_assets(gif_path)
    if asset_path is None:
        return None

    window = OverlayWindow(asset_path, config or {})
    state.WINDOWS.append(window)
    window.show()
    remove_native_border(window)
    if save:
        save_config()
    refresh_control_panel()
    return window


class OverlayWindow(QWidget):
    def __init__(self, gif_path, config=None):
        super().__init__()
        config = config or {}

        self.gif_path = Path(gif_path).resolve()
        self.locked = bool(config.get("locked", False))
        self.always_on_top = bool(config.get("always_on_top", True))
        self.click_through = bool(config.get("click_through", False))
        self.scale = int(config.get("scale", 100))
        self.opacity = int(config.get("opacity", 100))
        self.speed = int(config.get("speed", 100))
        self.drag_offset = QPoint()
        self.base_size = QSize()

        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet("background: transparent; border: 0; margin: 0; padding: 0;")

        self.movie = QMovie(str(self.gif_path))
        self.movie.setCacheMode(QMovie.CacheAll)
        self.movie.setSpeed(self.speed)

        size = QImageReader(str(self.gif_path)).size()
        if not size.isValid():
            size = self.movie.frameRect().size()
        if size.isValid():
            self.base_size = size
            self.apply_scale()

        self.apply_window_flags()
        self.apply_click_through()
        self.setWindowOpacity(self.opacity / 100)

        x = int(config.get("x", 100))
        y = int(config.get("y", 100))
        self.move(self.clamped_position(QPoint(x, y)))

        self.movie.frameChanged.connect(self.resize_to_movie)
        self.movie.start()
        self.resize_to_movie()

    def apply_window_flags(self):
        was_visible = self.isVisible()
        pos = self.pos()
        flags = Qt.FramelessWindowHint | Qt.Tool | Qt.NoDropShadowWindowHint
        if self.always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.move(self.clamped_position(pos))
        self.apply_click_through()
        if was_visible:
            self.show()
            self.raise_()
        remove_native_border(self)

    def apply_click_through(self):
        self.setAttribute(Qt.WA_TransparentForMouseEvents, self.click_through)
        self.update()

    def available_geometry(self):
        screen = QApplication.primaryScreen()
        return screen.availableGeometry() if screen else None

    def clamped_position(self, pos):
        geometry = self.available_geometry()
        if geometry is None:
            return pos

        max_x = max(geometry.left(), geometry.right() - max(1, self.width()) + 1)
        max_y = max(geometry.top(), geometry.bottom() - max(1, self.height()) + 1)
        x = min(max(pos.x(), geometry.left()), max_x)
        y = min(max(pos.y(), geometry.top()), max_y)
        return QPoint(x, y)

    def resize_to_movie(self):
        pixmap = self.movie.currentPixmap()
        size = pixmap.size()
        if size.isValid() and self.base_size != size:
            self.base_size = size
            self.apply_scale()
        self.update()

    def paintEvent(self, event):
        pixmap = self.movie.currentPixmap()
        if not pixmap.isNull():
            painter = QPainter(self)
            painter.setCompositionMode(QPainter.CompositionMode_Source)
            painter.drawPixmap(self.rect(), pixmap)

    def apply_scale(self):
        if not self.base_size.isValid():
            return
        width = max(1, round(self.base_size.width() * self.scale / 100))
        height = max(1, round(self.base_size.height() * self.scale / 100))
        self.setFixedSize(width, height)
        self.move(self.clamped_position(self.pos()))

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton and state.CONTROL_PANEL is not None:
            state.CONTROL_PANEL.select_window(self)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.locked:
            self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return

        if event.button() == Qt.RightButton:
            self.open_menu(event.globalPosition().toPoint())
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and not self.locked:
            self.move(self.clamped_position(event.globalPosition().toPoint() - self.drag_offset))
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.move(self.clamped_position(self.pos()))
            save_config()
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        self.open_menu(event.globalPos())

    def open_menu(self, pos):
        menu = QMenu(self)

        close_action = QAction("Close animation", self)
        close_action.triggered.connect(self.close)
        menu.addAction(close_action)

        lock_action = QAction("Unlock" if self.locked else "Lock", self)
        lock_action.triggered.connect(self.toggle_lock)
        menu.addAction(lock_action)

        top_action = QAction(
            "Disable always-on-top" if self.always_on_top else "Enable always-on-top",
            self,
        )
        top_action.triggered.connect(self.toggle_always_on_top)
        menu.addAction(top_action)

        click_action = QAction(
            "Disable click-through" if self.click_through else "Enable click-through",
            self,
        )
        click_action.triggered.connect(self.toggle_click_through)
        menu.addAction(click_action)

        scale_menu = menu.addMenu("Scale")
        for value in (50, 100, 150):
            scale_action = QAction(f"{value}%", self)
            scale_action.triggered.connect(lambda checked=False, scale=value: self.set_scale(scale))
            scale_menu.addAction(scale_action)

        menu.addSeparator()

        import_action = QAction("Import GIF...", self)
        import_action.triggered.connect(self.add_gif)
        menu.addAction(import_action)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(lambda: confirm_exit_or_tray(self))
        menu.addAction(exit_action)

        menu.exec(pos)

    def add_gif(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import GIF", str(BASE_DIR), "GIF files (*.gif)")
        if path:
            add_window(path)
            if state.CONTROL_PANEL is not None:
                state.CONTROL_PANEL.refresh_packs()

    def toggle_lock(self):
        self.locked = not self.locked
        save_config()
        refresh_control_panel()

    def toggle_always_on_top(self):
        self.always_on_top = not self.always_on_top
        self.apply_window_flags()
        save_config()
        refresh_control_panel()

    def showEvent(self, event):
        remove_native_border(self)
        super().showEvent(event)

    def toggle_click_through(self):
        self.click_through = not self.click_through
        self.apply_click_through()
        save_config()
        refresh_control_panel()

    def set_selected(self, selected):
        self.update()

    def set_scale(self, value):
        self.scale = int(value)
        self.apply_scale()
        save_config()

    def set_opacity_percent(self, value):
        self.opacity = int(value)
        self.setWindowOpacity(self.opacity / 100)
        save_config()

    def set_speed(self, value):
        self.speed = int(value)
        self.movie.setSpeed(self.speed)
        save_config()

    def to_config(self):
        pos = self.pos()
        return {
            "path": stored_path(self.gif_path),
            "x": pos.x(),
            "y": pos.y(),
            "locked": self.locked,
            "always_on_top": self.always_on_top,
            "click_through": self.click_through,
            "scale": self.scale,
            "opacity": self.opacity,
            "speed": self.speed,
        }

    def closeEvent(self, event):
        if state.EXITING:
            save_config()
            super().closeEvent(event)
            return

        save_config()
        if self in state.WINDOWS:
            state.WINDOWS.remove(self)
        save_config()
        refresh_control_panel()
        super().closeEvent(event)
