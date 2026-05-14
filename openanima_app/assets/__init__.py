from .facade import *  # noqa: F401,F403

from ..runtime import config as _runtime_config
from ..runtime import session as _runtime_session
from ..runtime.paths import CONFIG_PATH


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
