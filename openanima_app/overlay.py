import sys
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtGui import QAction, QImageReader, QMovie, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QFileDialog, QMenu, QMessageBox, QWidget

from .assets import (
    AssetType,
    detect_asset,
    frame_paths_for_folder,
    import_asset_to_assets,
    save_config,
    stored_path,
)
from .asset_validation import validate_asset_metadata
from .constants import BASE_DIR
from .frame_animation_player import FrameAnimationPlayer
from .metadata_renderers import (
    CompositeUIRenderer,
    SpriteAnimationPlayer,
    load_sprite_strip_frames,
    load_spritesheet_frames,
)
from . import state
from .logging_utils import log_info, log_warning


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
    log_info("OpenAnima exit requested")
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


def add_window(asset_path, config=None, save=True):
    path = Path(asset_path).resolve()
    asset = detect_asset(path)
    if asset is None and path.is_file():
        imported_path = import_asset_to_assets(path)
        asset = detect_asset(imported_path) if imported_path is not None else None

    if asset is None:
        log_warning("Unsupported or missing asset skipped: %s", asset_path)
        return None

    try:
        window = OverlayWindow(asset, config or {})
    except ValueError as exc:
        log_warning("%s", exc)
        return None
    state.WINDOWS.append(window)
    window.show()
    remove_native_border(window)
    log_info("Overlay created: %s", window.asset_path)
    if save:
        save_config()
    refresh_control_panel()
    return window


class OverlayWindow(QWidget):
    def __init__(self, asset, config=None):
        super().__init__()
        config = config or {}

        self.asset = asset
        self.asset_path = Path(asset.path).resolve()
        self.asset_type = asset.type
        self.gif_path = self.asset_path
        self.locked = bool(config.get("locked", False))
        self.always_on_top = bool(config.get("always_on_top", True))
        self.click_through = bool(config.get("click_through", False))
        self.scale = self.config_int(config, "scale", 100)
        self.opacity = self.config_int(config, "opacity", 100)
        self.speed = self.config_int(config, "speed", 100)
        self.drag_offset = QPoint()
        self.base_size = QSize()
        self.movie = None
        self.static_pixmap = QPixmap()
        self.current_pixmap = QPixmap()
        self.frame_player = None
        self.sprite_player = None
        self.composite_renderer = None
        layer_values = config.get("layer_values")
        self.layer_values = dict(layer_values) if isinstance(layer_values, dict) else {}
        current_animation = config.get("current_animation")
        self.current_animation = current_animation if isinstance(current_animation, str) else None

        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet("background: transparent; border: 0; margin: 0; padding: 0;")

        if not self.load_asset_content():
            raise ValueError(f"Unable to load asset: {self.asset_path}")

        self.apply_window_flags()
        self.apply_click_through()
        self.setWindowOpacity(self.opacity / 100)

        x = self.config_int(config, "x", 100)
        y = self.config_int(config, "y", 100)
        self.move(self.restored_position(QPoint(x, y)))

        self.start_playback()

    def load_asset_content(self):
        errors = validate_asset_metadata(self.asset)
        if errors:
            for error in errors:
                log_warning("%s: %s", self.asset.path, error)
            return False

        if self.asset_type == AssetType.GIF:
            self.movie = QMovie(str(self.asset_path))
            self.movie.setCacheMode(QMovie.CacheAll)
            self.movie.setSpeed(self.speed)

            size = QImageReader(str(self.asset_path)).size()
            if not size.isValid():
                size = self.movie.frameRect().size()
            if size.isValid():
                self.base_size = size
                self.apply_scale()

            self.movie.frameChanged.connect(self.update_from_movie)
            return True

        if self.asset_type == AssetType.STATIC_IMAGE:
            self.static_pixmap = QPixmap(str(self.asset_path))
            if self.static_pixmap.isNull():
                log_warning("Unreadable image skipped: %s", self.asset_path)
                return False
            self.current_pixmap = self.static_pixmap
            self.base_size = self.static_pixmap.size()
            self.apply_scale()
            return True

        if self.asset_type == AssetType.FRAME_ANIMATION:
            self.frame_player = FrameAnimationPlayer(
                frame_paths_for_folder(self.asset_path),
                fps=self.asset.fps or 12,
                parent=self,
            )
            self.frame_player.set_speed(self.speed)
            self.frame_player.pixmap_changed.connect(self.update_from_frame_player)
            if not self.frame_player.frames:
                log_warning("No readable frames in asset skipped: %s", self.asset_path)
                return False
            self.current_pixmap = self.frame_player.frames[0]
            self.base_size = self.current_pixmap.size()
            self.apply_scale()
            return True

        if self.asset_type == AssetType.SPRITE_STRIP:
            metadata = self.asset.metadata or {}
            frames = load_sprite_strip_frames(self.asset_path, metadata)
            if not frames:
                log_warning("No readable sprite strip frames in asset skipped: %s", self.asset_path)
                return False
            fps = metadata.get("fps", self.asset.fps or 8)
            loop = bool(metadata.get("loop", True))
            self.sprite_player = SpriteAnimationPlayer(frames, fps=fps, loop=loop, parent=self)
            self.sprite_player.set_speed(self.speed)
            self.sprite_player.pixmap_changed.connect(self.update_from_sprite_player)
            self.current_pixmap = frames[0]
            self.base_size = self.current_pixmap.size()
            self.apply_scale()
            return True

        if self.asset_type == AssetType.SPRITESHEET:
            metadata = self.asset.metadata or {}
            frames, fps, loop, selected_name = load_spritesheet_frames(self.asset_path, metadata, self.current_animation)
            if not frames:
                log_warning("No readable spritesheet frames in asset skipped: %s", self.asset_path)
                return False
            self.current_animation = selected_name
            self.sprite_player = SpriteAnimationPlayer(frames, fps=fps, loop=loop, parent=self)
            self.sprite_player.set_speed(self.speed)
            self.sprite_player.pixmap_changed.connect(self.update_from_sprite_player)
            self.current_pixmap = frames[0]
            self.base_size = self.current_pixmap.size()
            self.apply_scale()
            return True

        if self.asset_type == AssetType.COMPOSITE_UI:
            metadata = self._composite_metadata_with_runtime_values()
            self.composite_renderer = CompositeUIRenderer(self.asset_path, metadata)
            if not self.composite_renderer.layers:
                log_warning("No readable composite_ui layers in asset skipped: %s", self.asset_path)
                return False
            self.current_pixmap = self.composite_renderer.render()
            self.base_size = self.current_pixmap.size()
            self.apply_scale()
            return True

        return False

    def start_playback(self):
        if self.movie is not None:
            self.movie.start()
            self.update_from_movie()
        if self.frame_player is not None:
            self.frame_player.start()
        if self.sprite_player is not None:
            self.sprite_player.start()

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

    def visible_screen_geometry(self):
        screens = QApplication.screens()
        if not screens:
            return None

        geometry = QRect()
        for screen in screens:
            geometry = geometry.united(screen.availableGeometry()) if geometry.isValid() else screen.availableGeometry()
        return geometry

    def centered_on_primary_screen(self):
        geometry = self.available_geometry()
        if geometry is None:
            return QPoint(100, 100)

        return QPoint(
            geometry.left() + max(0, (geometry.width() - max(1, self.width())) // 2),
            geometry.top() + max(0, (geometry.height() - max(1, self.height())) // 2),
        )

    def restored_position(self, pos):
        visible_geometry = self.visible_screen_geometry()
        if visible_geometry is None:
            return pos

        window_rect = QRect(pos, self.size())
        if not window_rect.intersects(visible_geometry):
            return self.clamped_position(self.centered_on_primary_screen())

        return self.clamped_position(pos)

    def clamped_position(self, pos):
        geometry = self.available_geometry()
        if geometry is None:
            return pos

        max_x = max(geometry.left(), geometry.right() - max(1, self.width()) + 1)
        max_y = max(geometry.top(), geometry.bottom() - max(1, self.height()) + 1)
        x = min(max(pos.x(), geometry.left()), max_x)
        y = min(max(pos.y(), geometry.top()), max_y)
        return QPoint(x, y)

    def config_int(self, config, key, default):
        try:
            return int(config.get(key, default))
        except (TypeError, ValueError):
            return default

    def update_from_movie(self):
        pixmap = self.movie.currentPixmap()
        self.set_current_pixmap(pixmap)

    def update_from_frame_player(self, pixmap):
        self.set_current_pixmap(pixmap)

    def update_from_sprite_player(self, pixmap):
        self.set_current_pixmap(pixmap)

    def clipped_layer_values(self):
        if self.asset_type != AssetType.COMPOSITE_UI:
            return {}
        values = {}
        for layer in (self.asset.metadata or {}).get("layers", []):
            if not isinstance(layer, dict):
                continue
            if str(layer.get("clip") or "").lower() not in {"horizontal", "vertical"}:
                continue
            name = str(layer.get("name") or layer.get("image") or "layer")
            values[name] = float(self.layer_values.get(name, layer.get("value", 1.0)))
        return values

    def available_animations(self):
        animations = (self.asset.metadata or {}).get("animations")
        return list(animations.keys()) if self.asset_type == AssetType.SPRITESHEET and isinstance(animations, dict) else []

    def set_layer_value(self, layer_name, value):
        if self.asset_type != AssetType.COMPOSITE_UI:
            return
        value = min(1.0, max(0.0, float(value)))
        self.layer_values[str(layer_name)] = value
        if self.composite_renderer is not None:
            self.current_pixmap = self.composite_renderer.set_layer_value(str(layer_name), value)
            self.update()
        save_config()

    def set_animation(self, animation_name):
        if self.asset_type != AssetType.SPRITESHEET:
            return False
        animations = (self.asset.metadata or {}).get("animations")
        if not isinstance(animations, dict) or animation_name not in animations:
            return False
        if self.sprite_player is not None:
            self.sprite_player.stop()
            self.sprite_player.deleteLater()
            self.sprite_player = None
        frames, fps, loop, selected_name = load_spritesheet_frames(self.asset_path, self.asset.metadata or {}, animation_name)
        if not frames:
            return False
        self.current_animation = selected_name
        self.sprite_player = SpriteAnimationPlayer(frames, fps=fps, loop=loop, parent=self)
        self.sprite_player.set_speed(self.speed)
        self.sprite_player.pixmap_changed.connect(self.update_from_sprite_player)
        self.current_pixmap = frames[0]
        self.base_size = self.current_pixmap.size()
        self.apply_scale()
        self.sprite_player.start()
        save_config()
        return True

    def reload_asset_definition(self, new_asset_definition=None):
        old_state = {
            "asset": self.asset,
            "asset_type": self.asset_type,
            "base_size": self.base_size,
            "current_pixmap": self.current_pixmap,
            "movie": self.movie,
            "frame_player": self.frame_player,
            "sprite_player": self.sprite_player,
            "composite_renderer": self.composite_renderer,
        }
        self.stop_playback()
        if new_asset_definition is None:
            new_asset_definition = detect_asset(self.asset_path)
        if new_asset_definition is None:
            self._restore_renderer_state(old_state)
            return False

        self.asset = new_asset_definition
        self.asset_path = Path(new_asset_definition.path).resolve()
        self.asset_type = new_asset_definition.type
        self.movie = None
        self.frame_player = None
        self.sprite_player = None
        self.composite_renderer = None
        self.current_pixmap = QPixmap()
        if not self.load_asset_content():
            self._restore_renderer_state(old_state)
            log_warning("Overlay reload failed: %s", self.asset_path)
            return False
        self.start_playback()
        self.update()
        log_info("Overlay reloaded: %s", self.asset_path)
        return True

    def stop_playback(self):
        if self.movie is not None:
            self.movie.stop()
        if self.frame_player is not None:
            self.frame_player.stop()
        if self.sprite_player is not None:
            self.sprite_player.stop()

    def _restore_renderer_state(self, state_data):
        self.asset = state_data["asset"]
        self.asset_type = state_data["asset_type"]
        self.base_size = state_data["base_size"]
        self.current_pixmap = state_data["current_pixmap"]
        self.movie = state_data["movie"]
        self.frame_player = state_data["frame_player"]
        self.sprite_player = state_data["sprite_player"]
        self.composite_renderer = state_data["composite_renderer"]
        self.start_playback()

    def _composite_metadata_with_runtime_values(self):
        metadata = dict(self.asset.metadata or {})
        layers = []
        for layer in metadata.get("layers", []):
            if not isinstance(layer, dict):
                continue
            layer_copy = dict(layer)
            name = str(layer_copy.get("name") or layer_copy.get("image") or "layer")
            if name in self.layer_values:
                layer_copy["value"] = self.layer_values[name]
            layers.append(layer_copy)
        metadata["layers"] = layers
        return metadata

    def set_current_pixmap(self, pixmap):
        size = pixmap.size()
        if size.isValid() and self.base_size != size:
            self.base_size = size
            self.apply_scale()
        self.current_pixmap = pixmap
        self.update()

    def paintEvent(self, event):
        pixmap = self.current_pixmap
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

        close_action = QAction("Close asset", self)
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

        import_action = QAction("Import Asset...", self)
        import_action.triggered.connect(self.add_asset)
        menu.addAction(import_action)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(lambda: confirm_exit_or_tray(self))
        menu.addAction(exit_action)

        menu.exec(pos)

    def add_asset(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Asset",
            str(BASE_DIR),
            "Visual assets (*.gif *.png *.jpg *.jpeg *.webp)",
        )
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
        if self.movie is not None:
            self.movie.setSpeed(self.speed)
        if self.frame_player is not None:
            self.frame_player.set_speed(self.speed)
        if self.sprite_player is not None:
            self.sprite_player.set_speed(self.speed)
        save_config()

    def to_config(self):
        pos = self.pos()
        data = {
            "path": stored_path(self.asset_path),
            "asset_id": self.asset.id,
            "asset_type": self.asset_type,
            "x": pos.x(),
            "y": pos.y(),
            "locked": self.locked,
            "always_on_top": self.always_on_top,
            "click_through": self.click_through,
            "scale": self.scale,
            "opacity": self.opacity,
            "speed": self.speed,
        }
        if self.layer_values:
            data["layer_values"] = self.layer_values
        if self.current_animation:
            data["current_animation"] = self.current_animation
        return data

    def closeEvent(self, event):
        self.stop_playback()

        if state.EXITING:
            save_config()
            super().closeEvent(event)
            return

        save_config()
        if self in state.WINDOWS:
            state.WINDOWS.remove(self)
        log_info("Overlay removed: %s", self.asset_path)
        save_config()
        refresh_control_panel()
        super().closeEvent(event)
