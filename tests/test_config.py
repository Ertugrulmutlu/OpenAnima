import json
import shutil
import uuid
from pathlib import Path

from openanima_app.runtime import state
from openanima_app.assets import (
    CONFIG_SCHEMA_VERSION,
    atomic_write_json,
    load_config_data,
    normalize_config_data,
    persist_runtime_state,
    save_config,
)
from openanima_app.runtime.paths import DEFAULT_ASSETS_DIR


def runtime_dir():
    path = Path(".test_runtime_tmp") / uuid.uuid4().hex
    path.mkdir(parents=True)
    return path


def test_missing_config_file_uses_defaults():
    root = runtime_dir()
    try:
        config = load_config_data(root / "config.json")
    finally:
        shutil.rmtree(root)

    assert config["schema_version"] == CONFIG_SCHEMA_VERSION
    assert config["ui"] == {"control_panel_visible": True}
    assert config["windows"] == []
    assert state.ASSETS_DIR == DEFAULT_ASSETS_DIR


def test_invalid_json_is_backed_up_and_uses_defaults():
    root = runtime_dir()
    try:
        config_path = root / "config.json"
        config_path.write_text("{broken", encoding="utf-8")

        config = load_config_data(config_path)

        assert config["windows"] == []
        assert list(root.glob("config.corrupt.*.json"))
        assert config_path.read_text(encoding="utf-8") == "{broken"
    finally:
        shutil.rmtree(root)


def test_partial_config_uses_defaults_and_keeps_valid_windows():
    data = {
        "windows": [
            {
                "path": "assets/ok.gif",
                "x": 10,
                "action": {"enabled": True, "type": "open_url", "target": "https://example.com"},
                "movement": {"enabled": True, "velocity_x": 12},
            },
            {"x": 25},
            "assets/legacy.gif",
            42,
        ]
    }

    config = normalize_config_data(data)

    assert config["schema_version"] == CONFIG_SCHEMA_VERSION
    assert config["asset_root"] == "assets"
    assert config["ui"] == {"control_panel_visible": True}
    assert config["windows"] == [
        {
            "path": "assets/ok.gif",
            "x": 10,
            "action": {"enabled": True, "type": "open_url", "target": "https://example.com"},
            "movement": {"enabled": True, "velocity_x": 12},
        },
        {"path": "assets/legacy.gif"},
    ]


def test_atomic_save_creates_valid_json():
    root = runtime_dir()
    try:
        config_path = root / "config.json"

        atomic_write_json(config_path, {"schema_version": CONFIG_SCHEMA_VERSION, "windows": []})

        assert json.loads(config_path.read_text(encoding="utf-8")) == {
            "schema_version": CONFIG_SCHEMA_VERSION,
            "windows": [],
        }
        assert not list(root.glob("*.tmp"))
    finally:
        shutil.rmtree(root)


def test_old_config_without_schema_version_still_loads():
    root = runtime_dir()
    try:
        config_path = root / "config.json"
        config_path.write_text(json.dumps({"asset_root": "assets", "windows": [{"path": "assets/a.gif"}]}), encoding="utf-8")

        config = load_config_data(config_path)

        assert config["schema_version"] == CONFIG_SCHEMA_VERSION
        assert config["ui"] == {"control_panel_visible": True}
        assert config["windows"] == [{"path": "assets/a.gif"}]
    finally:
        shutil.rmtree(root)


def test_ui_config_is_normalized_and_saved():
    data = {
        "ui": {
            "control_panel_visible": False,
            "control_panel_geometry": {"x": "12", "y": 20, "width": 900, "height": 600},
            "last_page": "Settings",
        },
        "windows": [],
    }

    config = normalize_config_data(data)

    assert config["ui"] == {
        "control_panel_visible": False,
        "control_panel_geometry": {"x": 12, "y": 20, "width": 900, "height": 600},
        "last_page": "Settings",
    }


def test_save_config_preserves_hidden_ui_and_saved_overlay_failures(monkeypatch):
    root = runtime_dir()
    old_windows = list(state.WINDOWS)
    old_assets_dir = state.ASSETS_DIR
    old_preserved = list(state.PRESERVED_WINDOW_CONFIGS)
    old_ui = dict(state.UI_CONFIG)
    old_control_panel = state.CONTROL_PANEL
    try:
        config_path = root / "config.json"
        missing_overlay = {"path": "missing.gif", "x": 5}
        state.WINDOWS = []
        state.PRESERVED_WINDOW_CONFIGS = [missing_overlay]
        state.UI_CONFIG = {"control_panel_visible": False}
        state.CONTROL_PANEL = None

        import openanima_app.assets as assets_module

        monkeypatch.setattr(assets_module, "CONFIG_PATH", config_path)
        save_config()

        saved = json.loads(config_path.read_text(encoding="utf-8"))
        assert saved["ui"]["control_panel_visible"] is False
        assert saved["windows"] == [missing_overlay]
    finally:
        state.WINDOWS = old_windows
        state.ASSETS_DIR = old_assets_dir
        state.PRESERVED_WINDOW_CONFIGS = old_preserved
        state.UI_CONFIG = old_ui
        state.CONTROL_PANEL = old_control_panel
        shutil.rmtree(root)


def test_persist_runtime_state_skips_autosave_during_restore(monkeypatch):
    root = runtime_dir()
    old_restoring = state.RESTORING_SESSION
    old_windows = list(state.WINDOWS)
    old_control_panel = state.CONTROL_PANEL
    try:
        config_path = root / "config.json"
        config_path.write_text(json.dumps({"windows": [{"path": "saved.gif"}]}), encoding="utf-8")
        state.RESTORING_SESSION = True
        state.WINDOWS = []
        state.CONTROL_PANEL = None

        import openanima_app.assets as assets_module

        monkeypatch.setattr(assets_module, "CONFIG_PATH", config_path)
        assert persist_runtime_state("editor_initializing_defaults") is False
        assert json.loads(config_path.read_text(encoding="utf-8")) == {"windows": [{"path": "saved.gif"}]}
    finally:
        state.RESTORING_SESSION = old_restoring
        state.WINDOWS = old_windows
        state.CONTROL_PANEL = old_control_panel
        shutil.rmtree(root)


def test_forced_final_save_uses_same_runtime_persistence_during_restore(monkeypatch):
    root = runtime_dir()
    old_restoring = state.RESTORING_SESSION
    old_windows = list(state.WINDOWS)
    old_control_panel = state.CONTROL_PANEL
    try:
        config_path = root / "config.json"
        state.RESTORING_SESSION = True
        state.WINDOWS = []
        state.CONTROL_PANEL = None

        import openanima_app.assets as assets_module

        monkeypatch.setattr(assets_module, "CONFIG_PATH", config_path)
        assert persist_runtime_state("app_about_to_quit", force=True) is True
        assert json.loads(config_path.read_text(encoding="utf-8"))["windows"] == []
    finally:
        state.RESTORING_SESSION = old_restoring
        state.WINDOWS = old_windows
        state.CONTROL_PANEL = old_control_panel
        shutil.rmtree(root)
