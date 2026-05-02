import json

from openanima_app import state
from openanima_app.assets import (
    CONFIG_SCHEMA_VERSION,
    atomic_write_json,
    load_config_data,
    normalize_config_data,
)
from openanima_app.constants import DEFAULT_ASSETS_DIR


def test_missing_config_file_uses_defaults(tmp_path):
    config = load_config_data(tmp_path / "config.json")

    assert config["schema_version"] == CONFIG_SCHEMA_VERSION
    assert config["windows"] == []
    assert state.ASSETS_DIR == DEFAULT_ASSETS_DIR


def test_invalid_json_is_backed_up_and_uses_defaults(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text("{broken", encoding="utf-8")

    config = load_config_data(config_path)

    assert config["windows"] == []
    assert list(tmp_path.glob("config.corrupt.*.json"))
    assert config_path.read_text(encoding="utf-8") == "{broken"


def test_partial_config_uses_defaults_and_keeps_valid_windows():
    data = {
        "windows": [
            {"path": "assets/ok.gif", "x": 10},
            {"x": 25},
            "assets/legacy.gif",
            42,
        ]
    }

    config = normalize_config_data(data)

    assert config["schema_version"] == CONFIG_SCHEMA_VERSION
    assert config["asset_root"] == "assets"
    assert config["windows"] == [
        {"path": "assets/ok.gif", "x": 10},
        {"path": "assets/legacy.gif"},
    ]


def test_atomic_save_creates_valid_json(tmp_path):
    config_path = tmp_path / "config.json"

    atomic_write_json(config_path, {"schema_version": CONFIG_SCHEMA_VERSION, "windows": []})

    assert json.loads(config_path.read_text(encoding="utf-8")) == {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "windows": [],
    }
    assert not list(tmp_path.glob("*.tmp"))


def test_old_config_without_schema_version_still_loads(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"asset_root": "assets", "windows": [{"path": "assets/a.gif"}]}), encoding="utf-8")

    config = load_config_data(config_path)

    assert config["schema_version"] == CONFIG_SCHEMA_VERSION
    assert config["windows"] == [{"path": "assets/a.gif"}]
