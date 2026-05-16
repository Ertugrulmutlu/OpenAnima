from types import SimpleNamespace

from openanima_app import local_api
from openanima_app.runtime import state
from openanima_app.runtime.overlay_ids import (
    generate_persistent_id,
    is_valid_persistent_id,
    next_runtime_id,
    persistent_id_from_config,
)
from openanima_app.runtime.session import serialize_overlay_window


class FakePoint:
    def x(self):
        return 10

    def y(self):
        return 20


class FakeOverlay:
    def __init__(self):
        self.runtime_id = next_runtime_id()
        self.persistent_id = generate_persistent_id()
        self.api_alias = ""
        self.asset_path = "C:/asset.gif"
        self.asset = SimpleNamespace(id="asset", metadata={})
        self.asset_type = "gif"
        self.locked = False
        self.always_on_top = True
        self.click_through = False
        self.scale = 100
        self.opacity = 100
        self.speed = 100
        self.intended_visible = True
        self.action = {"enabled": False, "type": "open_file", "target": ""}
        self.movement = {"enabled": False}
        self.layer_values = {}
        self.current_animation = None
        self._saved_window_config = {}

    def pos(self):
        return FakePoint()

    def width(self):
        return 100

    def height(self):
        return 100

    def available_animations(self):
        return []


def test_overlay_api_serialization_uses_persistent_public_id():
    overlay = FakeOverlay()

    payload = local_api.detailed_overlay_payload(overlay)

    assert payload["id"] == overlay.persistent_id
    assert payload["runtime_id"] == overlay.runtime_id
    assert payload["persistent_id"] == overlay.persistent_id
    assert is_valid_persistent_id(payload["persistent_id"])


def test_overlay_lookup_accepts_runtime_persistent_legacy_and_alias():
    old_windows = list(state.WINDOWS)
    try:
        overlay = FakeOverlay()
        overlay.api_alias = "main_cat"
        state.WINDOWS = [overlay]

        assert local_api.find_overlay(overlay.runtime_id) is overlay
        assert local_api.find_overlay(overlay.persistent_id) is overlay
        assert local_api.find_overlay(str(id(overlay))) is overlay
        assert local_api.find_overlay("main_cat") is overlay
    finally:
        state.WINDOWS = old_windows


def test_session_serialization_includes_persistent_id_and_alias():
    overlay = FakeOverlay()
    overlay.api_alias = "scene_overlay"

    config = serialize_overlay_window(overlay)

    assert config["runtime_id"] == overlay.runtime_id
    assert config["persistent_id"] == overlay.persistent_id
    assert config["api_alias"] == "scene_overlay"


def test_collision_safe_scene_config_generates_new_persistent_id():
    original = generate_persistent_id()
    used = {original}

    config = local_api.config_with_collision_safe_persistent_id({"persistent_id": original}, used)

    assert config["persistent_id"] != original
    assert is_valid_persistent_id(config["persistent_id"])
    assert config["persistent_id"] in used


def test_missing_persistent_id_migration_generates_valid_id():
    persistent_id = persistent_id_from_config({})

    assert is_valid_persistent_id(persistent_id)
