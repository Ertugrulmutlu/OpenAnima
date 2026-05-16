from .constants import (
    DEFAULT_FRAME_FPS,
    METADATA_ASSET_TYPES,
    SUPPORTED_ANIMATED_IMAGE_EXTENSIONS,
    SUPPORTED_ASSET_EXTENSIONS,
    SUPPORTED_IMAGE_EXTENSIONS,
    SUPPORTED_VIDEO_EXTENSIONS,
)
from .detection import _metadata_int, _metadata_preview, detect_asset, is_apng_file, pack_name_for
from .importer import ensure_assets_dir, import_asset_to_assets, import_folder_to_assets, import_gif_to_assets, seed_default_assets_dir
from .metadata import frame_paths_for_folder, load_metadata, metadata_int, metadata_preview
from .models import AssetDefinition, AssetType
from .paths import (
    is_inside_assets,
    is_supported_asset_file,
    is_supported_frame_file,
    natural_key,
    resolve_saved_asset_path,
    resolved_path,
    stored_path,
    unique_asset_path,
    unique_folder_path,
)
from .scanner import asset_packs, assets_for_pack, gifs_for_pack, scan_assets
from .thumbnails import make_thumbnail
from ..runtime.config import (
    CONFIG_SCHEMA_VERSION,
    DEFAULT_LOCAL_API_CONFIG,
    DEFAULT_UI_CONFIG,
    LOCKED_CONFIG_KEYS,
    UI_PAGE_NAMES,
    VISIBLE_CONFIG_KEYS,
    WINDOW_CONFIG_KEYS,
    atomic_write_json,
    backup_corrupt_config,
    config_bool,
    config_warning,
    corrupt_config_backup_path,
    default_config,
    load_config,
    load_config_data,
    normalize_config_data,
    normalize_control_panel_geometry,
    normalize_local_api_config,
    normalize_ui_config,
    normalize_window_config,
    window_config_locked,
    window_config_visible,
)
from ..runtime.paths import BASE_DIR, BUNDLED_ASSETS_DIR, CONFIG_PATH, DEFAULT_ASSETS_DIR
from ..runtime.session import (
    _config_int,
    apply_window_config,
    build_session_config,
    current_ui_config,
    persist_runtime_state,
    preserved_window_configs,
    save_config,
    save_ui_state,
    serialize_overlay_window,
)
from ..runtime import config as _runtime_config
from ..runtime import session as _runtime_session
from ..ui.styles import THUMBNAIL_SIZE


def _sync_legacy_config_path():
    _runtime_config.CONFIG_PATH = CONFIG_PATH
    _runtime_session.CONFIG_PATH = CONFIG_PATH


def load_config_data(config_path=None):
    _sync_legacy_config_path()
    return _runtime_config.load_config_data(CONFIG_PATH if config_path is None else config_path)


def load_config():
    _sync_legacy_config_path()
    return _runtime_config.load_config()


def persist_runtime_state(reason, windows=None, force_empty=False, ui=None, force=False):
    _sync_legacy_config_path()
    return _runtime_session.persist_runtime_state(
        reason,
        windows=windows,
        force_empty=force_empty,
        ui=ui,
        force=force,
    )


def save_config(windows=None, force_empty=False, ui=None, reason="legacy_save_config", force=False):
    _sync_legacy_config_path()
    return _runtime_session.save_config(
        windows=windows,
        force_empty=force_empty,
        ui=ui,
        reason=reason,
        force=force,
    )


def save_ui_state(visible=None, reason="ui_state_changed"):
    _sync_legacy_config_path()
    return _runtime_session.save_ui_state(visible=visible, reason=reason)
