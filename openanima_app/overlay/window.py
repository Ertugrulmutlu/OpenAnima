from pathlib import Path

from PySide6.QtCore import QElapsedTimer, QPoint, QSize, Qt, QTimer
from PySide6.QtGui import QImageReader, QMovie, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QWidget

from ..assets.detection import detect_asset
from ..assets.importer import import_asset_to_assets
from ..assets.metadata import frame_paths_for_folder
from ..assets.models import AssetType
from ..assets.validation import validate_asset_metadata
from ..rendering.apng_player import ApngAnimationPlayer
from ..rendering.frame_player import FrameAnimationPlayer
from ..rendering.metadata_renderers import (
    CompositeUIRenderer,
    SpriteAnimationPlayer,
    load_sprite_strip_frames,
    load_spritesheet_frames,
)
from ..rendering.video_renderer import DEFAULT_VIDEO_SIZE, VideoAssetRenderer
from ..runtime import state
from ..runtime.action_runner import normalized_action_config
from ..runtime.config import window_config_visible
from ..runtime.logging import log_info, log_warning
from ..runtime.paths import BASE_DIR
from ..runtime.session import apply_window_config, persist_runtime_state
from .movement import normalized_movement_config
from .actions import (
    confirm_exit_or_tray,
    refresh_control_panel,
    run_action as run_overlay_action,
    set_action as set_overlay_action,
    set_opacity_percent as set_overlay_opacity_percent,
    set_scale as set_overlay_scale,
    set_speed as set_overlay_speed,
    show_action_result as show_overlay_action_result,
    toggle_always_on_top as toggle_overlay_always_on_top,
    toggle_click_through as toggle_overlay_click_through,
    toggle_lock as toggle_overlay_lock,
)
from .menu import open_overlay_menu
from .movement import (
    advance_movement as advance_overlay_movement,
    set_movement as set_overlay_movement,
    update_movement_timer as update_overlay_movement_timer,
)
from .serialization import to_config as overlay_to_config
from .window_flags import (
    apply_click_through as apply_overlay_click_through,
    apply_window_flags as apply_overlay_window_flags,
    available_geometry as overlay_available_geometry,
    centered_on_primary_screen as overlay_centered_on_primary_screen,
    clamped_position as overlay_clamped_position,
    remove_native_border,
    restored_position as overlay_restored_position,
    visible_screen_geometry as overlay_visible_screen_geometry,
)


def exit_app(reason="normal_app_quit"):
    state.EXITING = True
    log_info("OpenAnima exit requested")
    persist_runtime_state(reason, force=True)
    app = QApplication.instance()
    if app is not None:
        app.quit()


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
        if save:
            QMessageBox.warning(None, "OpenAnima", str(exc))
        return None
    state.WINDOWS.append(window)
    if window.intended_visible:
        window.show()
        remove_native_border(window)
    log_info("Overlay created: %s", window.asset_path)
    if save:
        persist_runtime_state("overlay_added")
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
        self._saved_window_config = dict(config)
        self.locked = False
        self.always_on_top = True
        self.click_through = False
        self.scale = 100
        self.opacity = 100
        self.intended_visible = window_config_visible(config, default=True)
        self.speed = 100
        self.drag_offset = QPoint()
        self.base_size = QSize()
        self.movie = None
        self.load_error = ""
        self.static_pixmap = QPixmap()
        self.current_pixmap = QPixmap()
        self.frame_player = None
        self.apng_player = None
        self.video_renderer = None
        self.sprite_player = None
        self.composite_renderer = None
        self.layer_values = {}
        self.current_animation = None
        self.action = normalized_action_config(None)
        self.movement = normalized_movement_config(None)
        self.runtime_velocity_x = 0.0
        self.runtime_velocity_y = 0.0
        self.movement_timer = QTimer(self)
        self.movement_timer.setInterval(33)
        self.movement_timer.timeout.connect(self.advance_movement)
        self.movement_clock = QElapsedTimer()

        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self.setContentsMargins(0, 0, 0, 0)
        self.setStyleSheet("background: transparent; border: 0; margin: 0; padding: 0;")

        apply_window_config(self, config, restore_geometry=False, restore_visibility=False)

        if not self.load_asset_content():
            detail = self.load_error or f"Unable to load asset: {self.asset_path}"
            raise ValueError(detail)

        apply_window_config(self, config, restore_geometry=True, restore_visibility=False)
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

        if self.asset_type == AssetType.APNG:
            self.apng_player = ApngAnimationPlayer(self.asset_path, parent=self)
            if self.apng_player.frames:
                self.apng_player.set_speed(self.speed)
                self.apng_player.pixmap_changed.connect(self.update_from_apng_player)
                self.current_pixmap = self.apng_player.frames[0][0]
                self.base_size = self.current_pixmap.size()
                self.apply_scale()
                return True

            reader = QImageReader(str(self.asset_path))
            reader.setFormat(b"png")
            self.static_pixmap = QPixmap.fromImage(reader.read())
            if self.static_pixmap.isNull():
                self.load_error = f"APNG is recognized, but this Qt build could not read this file: {self.asset_path}"
                log_warning("%s", self.load_error)
                return False
            log_warning(
                "APNG was detected, but animated APNG playback is not supported by the current Qt backend. "
                "Showing first frame only. %s",
                self.apng_player.error,
            )
            self.current_pixmap = self.static_pixmap
            self.base_size = self.static_pixmap.size()
            self.apply_scale()
            return True

        if self.asset_type == AssetType.WEBM:
            try:
                self.video_renderer = VideoAssetRenderer(self.asset_path, parent=self)
            except Exception as exc:
                self.load_error = f"WebM was detected, but Qt Multimedia could not initialize playback: {exc}"
                log_warning("%s", self.load_error)
                return False
            self.video_renderer.set_speed(self.speed)
            self.video_renderer.pixmap_changed.connect(self.update_from_video_renderer)
            self.video_renderer.size_changed.connect(self.update_video_size)
            self.video_renderer.error_changed.connect(self.log_video_error)
            self.video_renderer.warning_changed.connect(self.show_video_warning)
            self.current_pixmap = QPixmap(*DEFAULT_VIDEO_SIZE)
            self.current_pixmap.fill(Qt.transparent)
            self.base_size = QSize(*DEFAULT_VIDEO_SIZE)
            self.apply_scale()
            log_warning("WebM playback uses Qt Multimedia; alpha transparency depends on the system Qt backend.")
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
        if self.apng_player is not None:
            self.apng_player.start()
        if self.video_renderer is not None:
            self.video_renderer.start()
        if self.sprite_player is not None:
            self.sprite_player.start()

    def apply_window_flags(self):
        apply_overlay_window_flags(self)

    def apply_click_through(self):
        apply_overlay_click_through(self)

    def available_geometry(self):
        return overlay_available_geometry()

    def visible_screen_geometry(self):
        return overlay_visible_screen_geometry()

    def centered_on_primary_screen(self):
        return overlay_centered_on_primary_screen(self)

    def restored_position(self, pos):
        return overlay_restored_position(self, pos)

    def clamped_position(self, pos):
        return overlay_clamped_position(self, pos)

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

    def update_from_apng_player(self, pixmap):
        self.set_current_pixmap(pixmap)

    def update_from_video_renderer(self, pixmap):
        self.set_current_pixmap(pixmap)

    def update_video_size(self, width, height):
        size = QSize(width, height)
        if size.isValid() and self.base_size != size:
            self.base_size = size
            self.apply_scale()

    def log_video_error(self, message):
        log_warning("%s", message)

    def show_video_warning(self, message):
        log_warning("%s", message)
        QMessageBox.warning(self, "WebM Playback", message)

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
        persist_runtime_state("layer_values_changed")

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
        persist_runtime_state("current_animation_changed")
        return True

    def reload_asset_definition(self, new_asset_definition=None):
        old_state = {
            "asset": self.asset,
            "asset_type": self.asset_type,
            "base_size": self.base_size,
            "current_pixmap": self.current_pixmap,
            "movie": self.movie,
            "frame_player": self.frame_player,
            "apng_player": self.apng_player,
            "video_renderer": self.video_renderer,
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
        self.apng_player = None
        self.video_renderer = None
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
        persist_runtime_state("asset_reloaded")
        return True

    def stop_playback(self):
        if self.movie is not None:
            self.movie.stop()
        if self.frame_player is not None:
            self.frame_player.stop()
        if self.apng_player is not None:
            self.apng_player.stop()
        if self.video_renderer is not None:
            self.video_renderer.release()
        if self.sprite_player is not None:
            self.sprite_player.stop()

    def _restore_renderer_state(self, state_data):
        self.asset = state_data["asset"]
        self.asset_type = state_data["asset_type"]
        self.base_size = state_data["base_size"]
        self.current_pixmap = state_data["current_pixmap"]
        self.movie = state_data["movie"]
        self.frame_player = state_data["frame_player"]
        self.apng_player = state_data["apng_player"]
        self.video_renderer = state_data["video_renderer"]
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
        if event.button() == Qt.LeftButton and event.modifiers() & Qt.ControlModifier:
            ok, message = self.run_action()
            if not ok and message:
                QMessageBox.warning(self, "Run Action", message)
            event.accept()
            return

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
            persist_runtime_state("overlay_moved")
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        self.open_menu(event.globalPos())

    def open_menu(self, pos):
        open_overlay_menu(self, pos, confirm_exit_or_tray)

    def add_asset(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Asset",
            str(BASE_DIR),
            "Visual assets (*.gif *.apng *.png *.jpg *.jpeg *.webp *.webm)",
        )
        if path:
            if state.CONTROL_PANEL is not None:
                state.CONTROL_PANEL.import_analyzed_path(Path(path), add_to_desktop=True)
            else:
                add_window(path)

    def toggle_lock(self):
        toggle_overlay_lock(self)

    def toggle_always_on_top(self):
        toggle_overlay_always_on_top(self)

    def showEvent(self, event):
        remove_native_border(self)
        super().showEvent(event)

    def set_intended_visible(self, visible):
        self.intended_visible = bool(visible)
        if self.intended_visible:
            self.show()
        else:
            self.hide()

    def toggle_click_through(self):
        toggle_overlay_click_through(self)

    def set_selected(self, selected):
        self.update()

    def set_scale(self, value):
        set_overlay_scale(self, value)

    def set_opacity_percent(self, value):
        set_overlay_opacity_percent(self, value)

    def set_speed(self, value):
        set_overlay_speed(self, value)

    def set_action(self, config):
        set_overlay_action(self, config)

    def run_action(self):
        return run_overlay_action(self)

    def show_action_result(self):
        show_overlay_action_result(self)

    def set_movement(self, config):
        set_overlay_movement(self, config)

    def update_movement_timer(self):
        update_overlay_movement_timer(self)

    def advance_movement(self):
        advance_overlay_movement(self)

    def to_config(self):
        return overlay_to_config(self)

    def closeEvent(self, event):
        self.movement_timer.stop()
        self.stop_playback()

        if state.EXITING:
            persist_runtime_state("overlay_close_while_exiting", force=True)
            super().closeEvent(event)
            return

        if event.spontaneous():
            state.EXITING = True
            persist_runtime_state("windows_shutdown_close_event", force=True)
            super().closeEvent(event)
            return

        self.intended_visible = False
        if self in state.WINDOWS:
            state.WINDOWS.remove(self)
        log_info("Overlay removed: %s", self.asset_path)
        persist_runtime_state("overlay_removed")
        refresh_control_panel()
        super().closeEvent(event)
