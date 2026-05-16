import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from . import state
from .logging import log_warning
from .paths import CONFIG_PATH, DEFAULT_ASSETS_DIR
from ..assets.paths import resolved_path, stored_path


CONFIG_SCHEMA_VERSION = 1
WINDOW_CONFIG_KEYS = {
    "path",
    "gif_path",
    "asset_path",
    "asset_id",
    "asset_type",
    "runtime_id",
    "persistent_id",
    "api_alias",
    "x",
    "y",
    "locked",
    "always_on_top",
    "click_through",
    "scale",
    "opacity",
    "speed",
    "layer_values",
    "current_animation",
    "action",
    "movement",
    "visible",
    "intended_visible",
}
LOCKED_CONFIG_KEYS = ("locked", "is_locked")
VISIBLE_CONFIG_KEYS = ("intended_visible", "visible", "is_visible", "shown")
DEFAULT_UI_CONFIG = {
    "control_panel_visible": True,
}
DEFAULT_LOCAL_API_CONFIG = {
    "enabled": False,
    "token": "",
}
UI_PAGE_NAMES = {"Library", "Desktop", "Settings", "Local API", "Diagnostics", "About"}


def config_warning(message):
    log_warning(message)


def default_config():
    return {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "asset_root": stored_path(DEFAULT_ASSETS_DIR),
        "ui": DEFAULT_UI_CONFIG.copy(),
        "local_api": DEFAULT_LOCAL_API_CONFIG.copy(),
        "windows": [],
    }


def corrupt_config_backup_path(config_path):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return config_path.with_name(f"{config_path.stem}.corrupt.{timestamp}{config_path.suffix}")


def backup_corrupt_config(config_path):
    backup_path = corrupt_config_backup_path(config_path)
    try:
        shutil.copy2(config_path, backup_path)
        config_warning(f"Invalid config backed up to {backup_path}")
    except OSError as exc:
        config_warning(f"Invalid config could not be backed up: {exc}")
    return backup_path


def normalize_window_config(item):
    if isinstance(item, str):
        return {"path": item} if item else None

    if not isinstance(item, dict):
        config_warning("Skipped saved overlay with invalid entry type.")
        return None

    path_value = item.get("path") or item.get("gif_path") or item.get("asset_path")
    if not isinstance(path_value, str) or not path_value.strip():
        config_warning("Skipped saved overlay without a valid asset path.")
        return None

    normalized = dict(item)
    normalized["path"] = path_value
    if "locked" not in normalized:
        if any(key in item for key in LOCKED_CONFIG_KEYS[1:]):
            normalized["locked"] = window_config_locked(item)
    if "visible" not in normalized:
        if any(key in item for key in (*VISIBLE_CONFIG_KEYS[1:], "hidden")):
            normalized["visible"] = window_config_visible(item)
    return normalized


def config_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    if value is None:
        return default
    return bool(value)


def window_config_locked(config, default=False):
    if not isinstance(config, dict):
        return default

    for key in LOCKED_CONFIG_KEYS:
        if key in config:
            return config_bool(config.get(key), default=default)

    return default


def window_config_visible(config, default=True):
    if not isinstance(config, dict):
        return default

    for key in VISIBLE_CONFIG_KEYS:
        if key in config:
            return config_bool(config.get(key), default=default)

    if "hidden" in config:
        return not config_bool(config.get("hidden"), default=not default)

    return default


def normalize_control_panel_geometry(geometry):
    if not isinstance(geometry, dict):
        return None

    normalized = {}
    for key in ("x", "y", "width", "height"):
        try:
            normalized[key] = int(geometry[key])
        except (KeyError, TypeError, ValueError):
            return None

    if normalized["width"] <= 0 or normalized["height"] <= 0:
        return None
    return normalized


def normalize_ui_config(ui):
    normalized = DEFAULT_UI_CONFIG.copy()
    if not isinstance(ui, dict):
        return normalized

    if "control_panel_visible" in ui:
        normalized["control_panel_visible"] = bool(ui.get("control_panel_visible"))

    geometry = normalize_control_panel_geometry(ui.get("control_panel_geometry"))
    if geometry is not None:
        normalized["control_panel_geometry"] = geometry

    last_page = ui.get("last_page")
    if isinstance(last_page, str) and last_page in UI_PAGE_NAMES:
        normalized["last_page"] = last_page

    return normalized


def normalize_local_api_config(local_api):
    normalized = DEFAULT_LOCAL_API_CONFIG.copy()
    if not isinstance(local_api, dict):
        return normalized

    if "enabled" in local_api:
        normalized["enabled"] = config_bool(local_api.get("enabled"), default=False)

    token = local_api.get("token")
    if isinstance(token, str):
        normalized["token"] = token.strip()

    return normalized


def normalize_config_data(data):
    if isinstance(data, list):
        raw_windows = data
        asset_root = None
    elif isinstance(data, dict):
        schema_version = data.get("schema_version", 0)
        if schema_version not in (0, CONFIG_SCHEMA_VERSION):
            config_warning(f"Config schema version {schema_version} is newer than supported; attempting safe load.")

        asset_root = data.get("asset_root")
        ui = normalize_ui_config(data.get("ui"))
        local_api = normalize_local_api_config(data.get("local_api"))
        raw_windows = data.get("windows", [])
        if not isinstance(raw_windows, list):
            config_warning("Config windows field was invalid; starting with no saved overlays.")
            raw_windows = []
    else:
        config_warning("Config root was invalid; starting with safe defaults.")
        asset_root = None
        ui = DEFAULT_UI_CONFIG.copy()
        local_api = DEFAULT_LOCAL_API_CONFIG.copy()
        raw_windows = []

    if isinstance(data, list):
        ui = DEFAULT_UI_CONFIG.copy()
        local_api = DEFAULT_LOCAL_API_CONFIG.copy()

    if isinstance(asset_root, str) and asset_root.strip():
        state.ASSETS_DIR = resolved_path(asset_root).resolve()
    else:
        state.ASSETS_DIR = DEFAULT_ASSETS_DIR

    windows = []
    for item in raw_windows:
        normalized = normalize_window_config(item)
        if normalized is not None:
            windows.append(normalized)

    state.UI_CONFIG = ui.copy()
    state.LOCAL_API_CONFIG = local_api.copy()
    return {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "asset_root": stored_path(state.ASSETS_DIR),
        "ui": ui,
        "local_api": local_api,
        "windows": windows,
    }


def load_config_data(config_path=CONFIG_PATH):
    config_path = Path(config_path)
    if not config_path.exists():
        state.ASSETS_DIR = DEFAULT_ASSETS_DIR
        return default_config()

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        backup_corrupt_config(config_path)
        state.ASSETS_DIR = DEFAULT_ASSETS_DIR
        return default_config()
    except OSError as exc:
        config_warning(f"Could not read config: {exc}")
        state.ASSETS_DIR = DEFAULT_ASSETS_DIR
        return default_config()

    return normalize_config_data(data)


def atomic_write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    content = json.dumps(data, indent=2)

    with temp_path.open("w", encoding="utf-8") as file:
        file.write(content)
        file.write("\n")
        file.flush()
        os.fsync(file.fileno())

    os.replace(temp_path, path)
    try:
        directory = os.open(path.parent, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def load_config():
    return load_config_data(CONFIG_PATH)["windows"]
