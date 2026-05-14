from pathlib import Path

from PySide6.QtCore import QPoint

from . import state
from .config import (
    CONFIG_SCHEMA_VERSION,
    UI_PAGE_NAMES,
    atomic_write_json,
    config_bool,
    config_warning,
    normalize_ui_config,
    window_config_locked,
    window_config_visible,
)
from .logging import log_info
from .paths import CONFIG_PATH
from .action_runner import normalized_action_config
from ..assets.paths import stored_path
from ..overlay.movement import normalized_movement_config


def _config_int(config, key, default):
    try:
        return int(config.get(key, default))
    except (AttributeError, TypeError, ValueError):
        return default


def apply_window_config(overlay, config, restore_geometry=True, restore_visibility=False):
    config = config if isinstance(config, dict) else {}
    overlay._saved_window_config = dict(config)
    overlay.intended_visible = window_config_visible(config, default=True)

    overlay.locked = window_config_locked(config, default=False)
    overlay.always_on_top = config_bool(config.get("always_on_top"), default=True)
    overlay.click_through = config_bool(config.get("click_through"), default=False)
    overlay.scale = _config_int(config, "scale", 100)
    overlay.opacity = _config_int(config, "opacity", 100)
    overlay.speed = _config_int(config, "speed", 100)

    layer_values = config.get("layer_values")
    overlay.layer_values = dict(layer_values) if isinstance(layer_values, dict) else {}
    current_animation = config.get("current_animation")
    overlay.current_animation = current_animation if isinstance(current_animation, str) else None
    overlay.action = normalized_action_config(config.get("action"))
    overlay.movement = normalized_movement_config(config.get("movement"))
    overlay.runtime_velocity_x = float(overlay.movement.get("velocity_x", 0.0))
    overlay.runtime_velocity_y = float(overlay.movement.get("velocity_y", 0.0))

    if hasattr(overlay, "apply_window_flags"):
        overlay.apply_window_flags()
    if hasattr(overlay, "apply_click_through"):
        overlay.apply_click_through()
    if hasattr(overlay, "setWindowOpacity"):
        overlay.setWindowOpacity(overlay.opacity / 100)
    if hasattr(overlay, "apply_scale"):
        overlay.apply_scale()

    if restore_geometry and hasattr(overlay, "move"):
        x = _config_int(config, "x", 100)
        y = _config_int(config, "y", 100)
        pos = overlay.restored_position(QPoint(x, y)) if hasattr(overlay, "restored_position") else QPoint(x, y)
        overlay.move(pos)

    if restore_geometry and hasattr(overlay, "update_movement_timer"):
        overlay.update_movement_timer()

    if restore_visibility and hasattr(overlay, "show") and hasattr(overlay, "hide"):
        if overlay.intended_visible:
            overlay.show()
        else:
            overlay.hide()


def serialize_overlay_window(overlay):
    data = dict(getattr(overlay, "_saved_window_config", {}) or {})
    pos = overlay.pos()
    intended_visible = bool(getattr(overlay, "intended_visible", window_config_visible(data, default=True)))
    data.update(
        {
            "path": stored_path(overlay.asset_path),
            "asset_id": overlay.asset.id,
            "asset_type": overlay.asset_type,
            "x": pos.x(),
            "y": pos.y(),
            "locked": overlay.locked,
            "always_on_top": overlay.always_on_top,
            "click_through": overlay.click_through,
            "scale": overlay.scale,
            "opacity": overlay.opacity,
            "speed": overlay.speed,
            "visible": intended_visible,
            "intended_visible": intended_visible,
            "action": normalized_action_config(overlay.action),
            "movement": normalized_movement_config(overlay.movement),
        }
    )

    if overlay.layer_values:
        data["layer_values"] = dict(overlay.layer_values)
    if overlay.current_animation:
        data["current_animation"] = overlay.current_animation
    overlay._saved_window_config = dict(data)
    return data


def preserved_window_configs():
    live_paths = set()
    for window in state.WINDOWS:
        live_paths.add(stored_path(window.asset_path))
        live_paths.add(str(Path(window.asset_path).resolve()))

    preserved = []
    for config in state.PRESERVED_WINDOW_CONFIGS:
        if not isinstance(config, dict):
            continue
        path = config.get("path") or config.get("gif_path") or config.get("asset_path")
        if path in live_paths:
            continue
        preserved.append(config)
    return preserved


def current_ui_config(visible=None):
    ui = normalize_ui_config(state.UI_CONFIG)
    panel = state.CONTROL_PANEL
    if panel is None:
        return ui

    ui["control_panel_visible"] = panel.isVisible() if visible is None else bool(visible)
    geometry = panel.normalGeometry() if hasattr(panel, "normalGeometry") else panel.geometry()
    if geometry.isValid() and geometry.width() > 0 and geometry.height() > 0:
        ui["control_panel_geometry"] = {
            "x": geometry.x(),
            "y": geometry.y(),
            "width": geometry.width(),
            "height": geometry.height(),
        }
    if hasattr(panel, "current_page_name"):
        page_name = panel.current_page_name()
        if page_name in UI_PAGE_NAMES:
            ui["last_page"] = page_name

    state.UI_CONFIG = ui.copy()
    return ui


def save_ui_state(visible=None, reason="ui_state_changed"):
    persist_runtime_state(reason, ui=current_ui_config(visible=visible))


def build_session_config(windows=None, force_empty=False, ui=None):
    windows = state.WINDOWS if windows is None else windows
    window_configs = [serialize_overlay_window(window) for window in windows]

    if not force_empty:
        window_configs.extend(preserved_window_configs())

    ui_config = normalize_ui_config(ui if ui is not None else current_ui_config())
    data = {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "asset_root": stored_path(state.ASSETS_DIR),
        "ui": ui_config,
        "windows": window_configs,
    }
    return data


def persist_runtime_state(reason, windows=None, force_empty=False, ui=None, force=False):
    if state.RESTORING_SESSION and not force:
        log_info("Session save skipped during restore: %s", reason)
        return False

    data = build_session_config(windows=windows, force_empty=force_empty, ui=ui)
    try:
        atomic_write_json(CONFIG_PATH, data)
    except OSError as exc:
        config_warning(f"Could not save session ({reason}): {exc}")
        return False
    log_info("Session saved: %s", reason)
    return True


def save_config(windows=None, force_empty=False, ui=None, reason="legacy_save_config", force=False):
    return persist_runtime_state(
        reason,
        windows=windows,
        force_empty=force_empty,
        ui=ui,
        force=force,
    )
