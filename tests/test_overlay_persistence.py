import json
import os
import shutil
import uuid
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from openanima_app.runtime import state
from openanima_app.runtime.action_runner import ACTION_OPEN_URL
from openanima_app.assets import load_config_data, save_config
from openanima_app.app import restore_saved_windows, save_on_about_to_quit, tray_exit
import openanima_app.ui.control_panel.panel as control_panel_module
import openanima_app.overlay as overlay_module
from openanima_app.ui.control_panel.panel import ControlPanel
from openanima_app.overlay import OverlayWindow, add_window


def runtime_dir():
    path = Path(".test_runtime_tmp") / uuid.uuid4().hex
    path.mkdir(parents=True)
    return path


def app_instance():
    return QApplication.instance() or QApplication([])


class FakeCloseEvent:
    def __init__(self, spontaneous=False):
        self.accepted = False
        self.ignored = False
        self._spontaneous = spontaneous

    def spontaneous(self):
        return self._spontaneous

    def accept(self):
        self.accepted = True

    def ignore(self):
        self.ignored = True


@pytest.mark.parametrize(
    ("locked", "visible"),
    [
        (True, True),
        (False, True),
        (True, False),
        (False, False),
    ],
)
def test_lock_and_visibility_restore_exactly(monkeypatch, locked, visible):
    app_instance()
    old_windows = list(state.WINDOWS)
    old_control_panel = state.CONTROL_PANEL
    try:
        state.WINDOWS = []
        state.CONTROL_PANEL = None
        monkeypatch.setattr(OverlayWindow, "visible_screen_geometry", lambda self: None)
        monkeypatch.setattr(OverlayWindow, "available_geometry", lambda self: None)

        restored = add_window(
            Path("icon.png").resolve(),
            {
                "locked": locked,
                "visible": visible,
                "click_through": False,
                "always_on_top": True,
            },
            save=False,
        )

        assert restored is not None
        assert restored.locked is locked
        assert restored.isVisible() is visible
        assert restored.to_config()["locked"] is locked
        assert restored.to_config()["visible"] is visible
    finally:
        for window in list(state.WINDOWS):
            window.stop_playback()
            window.close()
        app_instance().processEvents()
        state.WINDOWS = old_windows
        state.CONTROL_PANEL = old_control_panel


@pytest.mark.parametrize(
    "visibility_config",
    [
        {"hidden": True},
        {"is_visible": False},
        {"shown": False},
    ],
)
def test_legacy_hidden_visibility_keys_restore_hidden(monkeypatch, visibility_config):
    app_instance()
    old_windows = list(state.WINDOWS)
    try:
        state.WINDOWS = []
        monkeypatch.setattr(OverlayWindow, "visible_screen_geometry", lambda self: None)
        monkeypatch.setattr(OverlayWindow, "available_geometry", lambda self: None)

        restored = add_window(
            Path("icon.png").resolve(),
            {"locked": False, **visibility_config},
            save=False,
        )

        assert restored is not None
        assert restored.isVisible() is False
        assert restored.locked is False
    finally:
        for window in list(state.WINDOWS):
            window.stop_playback()
            window.close()
        app_instance().processEvents()
        state.WINDOWS = old_windows


def test_legacy_locked_key_restores_locked(monkeypatch):
    app_instance()
    old_windows = list(state.WINDOWS)
    try:
        state.WINDOWS = []
        monkeypatch.setattr(OverlayWindow, "visible_screen_geometry", lambda self: None)
        monkeypatch.setattr(OverlayWindow, "available_geometry", lambda self: None)

        restored = add_window(
            Path("icon.png").resolve(),
            {"is_locked": True, "is_visible": "true"},
            save=False,
        )

        assert restored is not None
        assert restored.locked is True
        assert restored.isVisible() is True
        assert restored.to_config()["locked"] is True
        assert restored.to_config()["visible"] is True
    finally:
        for window in list(state.WINDOWS):
            window.stop_playback()
            window.close()
        app_instance().processEvents()
        state.WINDOWS = old_windows


def test_overlay_runtime_changes_are_serialized_before_exit(monkeypatch):
    app_instance()
    root = runtime_dir()
    old_windows = list(state.WINDOWS)
    old_control_panel = state.CONTROL_PANEL
    old_restoring = state.RESTORING_SESSION
    try:
        config_path = root / "config.json"
        state.WINDOWS = []
        state.CONTROL_PANEL = None
        state.RESTORING_SESSION = False
        monkeypatch.setattr(OverlayWindow, "visible_screen_geometry", lambda self: None)
        monkeypatch.setattr(OverlayWindow, "available_geometry", lambda self: None)

        import openanima_app.assets as assets_module

        monkeypatch.setattr(assets_module, "CONFIG_PATH", config_path)
        window = add_window(Path("icon.png").resolve(), save=True)
        window.set_scale(125)
        window.toggle_lock()
        window.set_intended_visible(False)
        assets_module.persist_runtime_state("overlay_visibility_changed")
        window.set_movement({"enabled": True, "velocity_x": 42, "velocity_y": 7, "bounce": False})

        saved = json.loads(config_path.read_text(encoding="utf-8"))["windows"][0]
        assert saved["scale"] == 125
        assert saved["locked"] is True
        assert saved["visible"] is False
        assert saved["movement"]["enabled"] is True
        assert saved["movement"]["velocity_x"] == 42.0
        assert saved["movement"]["bounce"] is False
    finally:
        for window in list(state.WINDOWS):
            window.stop_playback()
            window.close()
        app_instance().processEvents()
        state.WINDOWS = old_windows
        state.CONTROL_PANEL = old_control_panel
        state.RESTORING_SESSION = old_restoring
        shutil.rmtree(root)


def test_exit_paths_call_central_runtime_persistence(monkeypatch):
    calls = []
    old_exiting = state.EXITING
    try:
        state.EXITING = False
        monkeypatch.setattr(overlay_module, "persist_runtime_state", lambda reason, **kwargs: calls.append((reason, kwargs)))
        monkeypatch.setattr(overlay_module.QApplication, "instance", lambda: type("App", (), {"quit": lambda self: None})())
        overlay_module.exit_app("overlay_context_exit")
        assert calls[-1] == ("overlay_context_exit", {"force": True})

        calls.clear()
        state.EXITING = False
        monkeypatch.setattr(control_panel_module, "persist_runtime_state", lambda reason, **kwargs: calls.append((reason, kwargs)))
        monkeypatch.setattr(control_panel_module, "confirm_exit_or_tray", lambda parent=None: "exit")
        fake_panel = type("Panel", (), {"clear_overlay_selection": lambda self: None})()
        event = FakeCloseEvent()
        control_panel_module.ControlPanel.closeEvent(fake_panel, event)
        assert ("control_panel_close_event", {"force": True}) in calls
        assert event.accepted is True

        calls.clear()
        import openanima_app.app as app_module

        monkeypatch.setattr(app_module, "exit_app", lambda reason: calls.append((reason, {})))
        tray_exit()
        assert calls == [("tray_exit", {})]

        calls.clear()
        monkeypatch.setattr(app_module, "persist_runtime_state", lambda reason, **kwargs: calls.append((reason, kwargs)))
        save_on_about_to_quit()
        assert calls == [("app_about_to_quit", {"force": True})]
    finally:
        state.EXITING = old_exiting


def test_toggle_lock_and_visibility_save_and_reload(monkeypatch):
    app_instance()
    root = runtime_dir()
    old_windows = list(state.WINDOWS)
    old_control_panel = state.CONTROL_PANEL
    old_ui = dict(state.UI_CONFIG)
    try:
        config_path = root / "config.json"
        state.WINDOWS = []
        state.CONTROL_PANEL = None
        state.UI_CONFIG = {"control_panel_visible": False}
        monkeypatch.setattr(OverlayWindow, "visible_screen_geometry", lambda self: None)
        monkeypatch.setattr(OverlayWindow, "available_geometry", lambda self: None)

        import openanima_app.assets as assets_module

        monkeypatch.setattr(assets_module, "CONFIG_PATH", config_path)
        window = add_window(Path("icon.png").resolve(), save=False)
        assert window is not None

        window.toggle_lock()
        loaded = load_config_data(config_path)["windows"][0]
        assert loaded["locked"] is True
        state.WINDOWS = []
        restored = add_window(Path("icon.png").resolve(), loaded, save=False)
        assert restored.locked is True

        panel = ControlPanel()
        state.CONTROL_PANEL = panel
        panel.toggle_overlay_visible(restored)
        hidden_config = load_config_data(config_path)["windows"][0]
        assert hidden_config["visible"] is False
        state.WINDOWS = []
        restored_hidden = add_window(Path("icon.png").resolve(), hidden_config, save=False)
        assert restored_hidden.isVisible() is False

        panel.toggle_overlay_visible(restored_hidden)
        visible_config = load_config_data(config_path)["windows"][0]
        assert visible_config["visible"] is True
        assert visible_config["locked"] is True
        state.WINDOWS = []
        restored_visible = add_window(Path("icon.png").resolve(), visible_config, save=False)
        assert restored_visible.isVisible() is True
        assert restored_visible.locked is True

        panel.hide()
        panel.deleteLater()
    finally:
        for window in list(state.WINDOWS):
            window.stop_playback()
            window.close()
        app_instance().processEvents()
        state.WINDOWS = old_windows
        state.CONTROL_PANEL = old_control_panel
        state.UI_CONFIG = old_ui
        shutil.rmtree(root)


def test_hidden_control_panel_state_does_not_hide_visible_overlay(monkeypatch):
    app_instance()
    root = runtime_dir()
    old_windows = list(state.WINDOWS)
    old_control_panel = state.CONTROL_PANEL
    old_ui = dict(state.UI_CONFIG)
    try:
        config_path = root / "config.json"
        state.WINDOWS = []
        state.CONTROL_PANEL = None
        state.UI_CONFIG = {"control_panel_visible": False}
        monkeypatch.setattr(OverlayWindow, "visible_screen_geometry", lambda self: None)
        monkeypatch.setattr(OverlayWindow, "available_geometry", lambda self: None)

        import openanima_app.assets as assets_module

        monkeypatch.setattr(assets_module, "CONFIG_PATH", config_path)
        window = add_window(Path("icon.png").resolve(), {"visible": True}, save=False)
        assert window is not None

        save_config()

        saved = json.loads(config_path.read_text(encoding="utf-8"))
        assert saved["ui"]["control_panel_visible"] is False
        assert saved["windows"][0]["visible"] is True
    finally:
        for window in list(state.WINDOWS):
            window.stop_playback()
            window.close()
        app_instance().processEvents()
        state.WINDOWS = old_windows
        state.CONTROL_PANEL = old_control_panel
        state.UI_CONFIG = old_ui
        shutil.rmtree(root)


def test_shutdown_save_uses_intended_visibility_when_qt_runtime_hides_overlay(monkeypatch):
    app_instance()
    root = runtime_dir()
    old_windows = list(state.WINDOWS)
    old_control_panel = state.CONTROL_PANEL
    old_ui = dict(state.UI_CONFIG)
    old_exiting = state.EXITING
    try:
        config_path = root / "config.json"
        state.WINDOWS = []
        state.CONTROL_PANEL = None
        state.UI_CONFIG = {"control_panel_visible": False}
        state.EXITING = False
        monkeypatch.setattr(OverlayWindow, "visible_screen_geometry", lambda self: None)
        monkeypatch.setattr(OverlayWindow, "available_geometry", lambda self: None)

        import openanima_app.assets as assets_module

        monkeypatch.setattr(assets_module, "CONFIG_PATH", config_path)
        window = add_window(Path("icon.png").resolve(), {"visible": True}, save=False)
        assert window is not None
        assert window.intended_visible is True
        assert window.isVisible() is True

        window.hide()
        assert window.intended_visible is True
        assert window.isVisible() is False

        save_config(reason="windows_shutdown_close_event", force=True)
        saved = json.loads(config_path.read_text(encoding="utf-8"))["windows"][0]
        assert saved["visible"] is True
        assert saved["intended_visible"] is True

        state.WINDOWS = []
        restored = add_window(Path("icon.png").resolve(), saved, save=False)
        assert restored is not None
        assert restored.intended_visible is True
        assert restored.isVisible() is True
    finally:
        for window in list(state.WINDOWS):
            window.stop_playback()
            window.close()
        app_instance().processEvents()
        state.WINDOWS = old_windows
        state.CONTROL_PANEL = old_control_panel
        state.UI_CONFIG = old_ui
        state.EXITING = old_exiting
        shutil.rmtree(root)


def test_explicit_hidden_overlay_stays_hidden_across_shutdown_save(monkeypatch):
    app_instance()
    root = runtime_dir()
    old_windows = list(state.WINDOWS)
    old_control_panel = state.CONTROL_PANEL
    old_ui = dict(state.UI_CONFIG)
    try:
        config_path = root / "config.json"
        state.WINDOWS = []
        state.CONTROL_PANEL = None
        state.UI_CONFIG = {"control_panel_visible": False}
        monkeypatch.setattr(OverlayWindow, "visible_screen_geometry", lambda self: None)
        monkeypatch.setattr(OverlayWindow, "available_geometry", lambda self: None)

        import openanima_app.assets as assets_module

        monkeypatch.setattr(assets_module, "CONFIG_PATH", config_path)
        window = add_window(Path("icon.png").resolve(), {"visible": True}, save=False)
        assert window is not None

        window.set_intended_visible(False)
        save_config(reason="windows_shutdown_close_event", force=True)
        saved = json.loads(config_path.read_text(encoding="utf-8"))["windows"][0]
        assert saved["visible"] is False
        assert saved["intended_visible"] is False

        state.WINDOWS = []
        restored = add_window(Path("icon.png").resolve(), saved, save=False)
        assert restored is not None
        assert restored.intended_visible is False
        assert restored.isVisible() is False
    finally:
        for window in list(state.WINDOWS):
            window.stop_playback()
            window.close()
        app_instance().processEvents()
        state.WINDOWS = old_windows
        state.CONTROL_PANEL = old_control_panel
        state.UI_CONFIG = old_ui
        shutil.rmtree(root)


def test_tray_minimized_control_panel_does_not_change_overlay_intent(monkeypatch):
    app_instance()
    root = runtime_dir()
    old_windows = list(state.WINDOWS)
    old_control_panel = state.CONTROL_PANEL
    old_ui = dict(state.UI_CONFIG)
    try:
        config_path = root / "config.json"
        state.WINDOWS = []
        state.CONTROL_PANEL = None
        state.UI_CONFIG = {"control_panel_visible": True}
        monkeypatch.setattr(OverlayWindow, "visible_screen_geometry", lambda self: None)
        monkeypatch.setattr(OverlayWindow, "available_geometry", lambda self: None)

        import openanima_app.assets as assets_module

        monkeypatch.setattr(assets_module, "CONFIG_PATH", config_path)
        window = add_window(Path("icon.png").resolve(), {"visible": True}, save=False)
        assert window is not None

        panel = ControlPanel()
        state.CONTROL_PANEL = panel
        panel.hide()
        save_config(reason="control_panel_hidden")

        saved = json.loads(config_path.read_text(encoding="utf-8"))
        assert saved["ui"]["control_panel_visible"] is False
        assert saved["windows"][0]["visible"] is True
        assert saved["windows"][0]["intended_visible"] is True
        assert window.intended_visible is True

        panel.deleteLater()
    finally:
        for window in list(state.WINDOWS):
            window.stop_playback()
            window.close()
        app_instance().processEvents()
        state.WINDOWS = old_windows
        state.CONTROL_PANEL = old_control_panel
        state.UI_CONFIG = old_ui
        shutil.rmtree(root)


def test_action_and_movement_save_load_restore_runtime_and_editor(monkeypatch):
    app_instance()
    root = runtime_dir()
    old_windows = list(state.WINDOWS)
    old_control_panel = state.CONTROL_PANEL
    old_assets_dir = state.ASSETS_DIR
    old_preserved = list(state.PRESERVED_WINDOW_CONFIGS)
    try:
        config_path = root / "config.json"
        asset_path = Path("demo.gif").resolve()
        state.WINDOWS = []
        state.CONTROL_PANEL = None
        monkeypatch.setattr(OverlayWindow, "visible_screen_geometry", lambda self: None)
        monkeypatch.setattr(OverlayWindow, "available_geometry", lambda self: None)

        import openanima_app.assets as assets_module

        monkeypatch.setattr(assets_module, "CONFIG_PATH", config_path)
        window = add_window(asset_path, save=False)
        assert window is not None
        window.set_action({"enabled": True, "type": ACTION_OPEN_URL, "target": "https://example.com"})
        window.set_movement(
            {
                "enabled": False,
                "velocity_x": 42.0,
                "velocity_y": -7.0,
                "bounce": False,
                "gravity": 3.0,
                "friction": 0.5,
            }
        )
        window.locked = True
        window.always_on_top = False
        window.click_through = True
        window.set_scale(125)
        window.set_opacity_percent(80)
        window.set_speed(75)
        window.move(33, 44)

        save_config()
        saved = json.loads(config_path.read_text(encoding="utf-8"))
        assert saved["windows"][0]["x"] == 33
        assert saved["windows"][0]["y"] == 44
        assert saved["windows"][0]["scale"] == 125
        assert saved["windows"][0]["opacity"] == 80
        assert saved["windows"][0]["speed"] == 75
        assert saved["windows"][0]["visible"] is True
        assert saved["windows"][0]["locked"] is True
        assert saved["windows"][0]["always_on_top"] is False
        assert saved["windows"][0]["click_through"] is True
        assert saved["windows"][0]["action"]["target"] == "https://example.com"
        assert saved["windows"][0]["movement"]["velocity_x"] == 42.0
        assert saved["windows"][0]["movement"]["enabled"] is False

        loaded_config = load_config_data(config_path)["windows"][0]
        window.close()
        state.WINDOWS = []

        restored = add_window(asset_path, loaded_config, save=False)
        assert restored is not None
        assert state.WINDOWS == [restored]
        assert restored.x() == 33
        assert restored.y() == 44
        assert restored.scale == 125
        assert restored.opacity == 80
        assert restored.speed == 75
        assert restored.isVisible() is True
        assert restored.locked is True
        assert restored.always_on_top is False
        assert restored.click_through is True
        assert restored.action["enabled"] is True
        assert restored.action["type"] == ACTION_OPEN_URL
        assert restored.action["target"] == "https://example.com"
        assert restored.movement["enabled"] is False
        assert restored.movement["velocity_x"] == 42.0
        assert restored.movement["bounce"] is False

        panel = ControlPanel()
        state.CONTROL_PANEL = panel
        panel.load_editor(restored)
        assert panel.action_enabled_check.isChecked() is True
        assert panel.action_type_combo.currentData() == ACTION_OPEN_URL
        assert panel.action_target_edit.text() == "https://example.com"
        assert panel.movement_enabled_check.isChecked() is False
        assert panel.movement_vx_spin.value() == 42.0
        assert panel.movement_bounce_check.isChecked() is False
        panel.hide()
        panel.deleteLater()
        restored.stop_playback()
        restored.close()
        app_instance().processEvents()
    finally:
        for window in list(state.WINDOWS):
            window.stop_playback()
            window.close()
        app_instance().processEvents()
        state.WINDOWS = old_windows
        state.CONTROL_PANEL = old_control_panel
        state.ASSETS_DIR = old_assets_dir
        state.PRESERVED_WINDOW_CONFIGS = old_preserved
        shutil.rmtree(root)


def test_full_window_config_round_trip_preserves_restored_state_and_unknown_fields(monkeypatch):
    app_instance()
    root = runtime_dir()
    old_windows = list(state.WINDOWS)
    old_control_panel = state.CONTROL_PANEL
    old_assets_dir = state.ASSETS_DIR
    old_preserved = list(state.PRESERVED_WINDOW_CONFIGS)
    old_ui = dict(state.UI_CONFIG)
    try:
        config_path = root / "config.json"
        state.WINDOWS = []
        state.CONTROL_PANEL = None
        state.PRESERVED_WINDOW_CONFIGS = []
        monkeypatch.setattr(OverlayWindow, "visible_screen_geometry", lambda self: None)
        monkeypatch.setattr(OverlayWindow, "available_geometry", lambda self: None)

        import openanima_app.assets as assets_module

        monkeypatch.setattr(assets_module, "CONFIG_PATH", config_path)
        entry = {
            "path": "icon.png",
            "asset_id": "icon.png",
            "asset_type": "static_image",
            "x": 21,
            "y": 34,
            "locked": True,
            "always_on_top": True,
            "click_through": False,
            "scale": 137,
            "opacity": 62,
            "speed": 143,
            "visible": True,
            "action": {
                "enabled": True,
                "type": ACTION_OPEN_URL,
                "target": "https://example.com/openanima",
                "custom_action_value": "keep-me",
            },
            "movement": {
                "enabled": True,
                "velocity_x": 2.5,
                "velocity_y": -1.5,
                "bounce": True,
                "gravity": 5.0,
                "friction": 0.25,
                "custom_movement_value": 99,
            },
            "current_animation": "idle",
            "layer_values": {"eyes": 0.42},
            "future_window_value": {"nested": ["preserve"]},
        }
        config_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "asset_root": "assets",
                    "ui": {"control_panel_visible": False, "last_page": "Desktop"},
                    "windows": [entry],
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        config = load_config_data(config_path)
        restored, failed = restore_saved_windows(config["windows"], asset_root=state.ASSETS_DIR)

        assert restored == 1
        assert failed == []
        window = state.WINDOWS[0]
        assert window.locked is True
        assert window.isVisible() is True
        assert window.always_on_top is True
        assert window.click_through is False
        assert window.scale == 137
        assert window.opacity == 62
        assert window.speed == 143
        assert window.action["enabled"] is True
        assert window.action["type"] == ACTION_OPEN_URL
        assert window.action["target"] == "https://example.com/openanima"
        assert window.action["custom_action_value"] == "keep-me"
        assert window.movement["enabled"] is True
        assert window.movement["velocity_x"] == 2.5
        assert window.movement["velocity_y"] == -1.5
        assert window.movement["bounce"] is True
        assert window.movement["gravity"] == 5.0
        assert window.movement["friction"] == 0.25
        assert window.movement["custom_movement_value"] == 99

        save_config()
        saved = json.loads(config_path.read_text(encoding="utf-8"))["windows"][0]
        for key in (
            "locked",
            "visible",
            "always_on_top",
            "click_through",
            "scale",
            "opacity",
            "speed",
            "current_animation",
            "layer_values",
            "future_window_value",
        ):
            assert saved[key] == entry[key]
        assert saved["action"] == entry["action"]
        assert saved["movement"] == entry["movement"]

        panel = ControlPanel()
        state.CONTROL_PANEL = panel
        panel.load_editor(window)
        save_config()
        after_editor = json.loads(config_path.read_text(encoding="utf-8"))["windows"][0]
        assert after_editor["action"] == entry["action"]
        assert after_editor["movement"] == entry["movement"]
        assert after_editor["locked"] is True
        assert after_editor["visible"] is True
        panel.hide()
        panel.deleteLater()
    finally:
        for window in list(state.WINDOWS):
            window.stop_playback()
            window.close()
        app_instance().processEvents()
        state.WINDOWS = old_windows
        state.CONTROL_PANEL = old_control_panel
        state.ASSETS_DIR = old_assets_dir
        state.PRESERVED_WINDOW_CONFIGS = old_preserved
        state.UI_CONFIG = old_ui
        shutil.rmtree(root)


def test_restore_saved_windows_resolves_paths_inside_asset_root(monkeypatch):
    app_instance()
    root = runtime_dir()
    old_windows = list(state.WINDOWS)
    old_control_panel = state.CONTROL_PANEL
    old_assets_dir = state.ASSETS_DIR
    try:
        asset_root = root / "assets"
        asset_root.mkdir()
        asset_path = asset_root / "restored.png"
        shutil.copy2(Path("icon.png"), asset_path)
        state.WINDOWS = []
        state.CONTROL_PANEL = None
        state.ASSETS_DIR = asset_root
        monkeypatch.setattr(OverlayWindow, "visible_screen_geometry", lambda self: None)
        monkeypatch.setattr(OverlayWindow, "available_geometry", lambda self: None)

        restored, failed = restore_saved_windows(
            [
                    {
                        "path": "restored.png",
                    "x": 12,
                    "y": 18,
                    "scale": 90,
                    "opacity": 70,
                    "visible": False,
                    "action": {"enabled": True, "type": ACTION_OPEN_URL, "target": "https://example.com"},
                    "movement": {"enabled": False, "velocity_x": 8.0},
                }
            ],
            asset_root=asset_root,
        )

        assert restored == 1
        assert failed == []
        assert len(state.WINDOWS) == 1
        window = state.WINDOWS[0]
        assert window.asset_path == asset_path.resolve()
        assert window.x() == 12
        assert window.y() == 18
        assert window.scale == 90
        assert window.opacity == 70
        assert window.isVisible() is False
        assert window.action["target"] == "https://example.com"
        assert window.movement["velocity_x"] == 8.0
        window.stop_playback()
        window.close()
        app_instance().processEvents()
    finally:
        for window in list(state.WINDOWS):
            window.stop_playback()
            window.close()
        app_instance().processEvents()
        state.WINDOWS = old_windows
        state.CONTROL_PANEL = old_control_panel
        state.ASSETS_DIR = old_assets_dir
        state.PRESERVED_WINDOW_CONFIGS = []
        shutil.rmtree(root)


def test_failed_restore_preserves_saved_windows_on_next_save(monkeypatch):
    root = runtime_dir()
    old_windows = list(state.WINDOWS)
    old_assets_dir = state.ASSETS_DIR
    old_preserved = list(state.PRESERVED_WINDOW_CONFIGS)
    try:
        config_path = root / "config.json"
        state.WINDOWS = []
        state.ASSETS_DIR = root / "assets"
        missing_config = {"path": "missing.gif", "x": 7, "scale": 130}

        import openanima_app.assets as assets_module

        monkeypatch.setattr(assets_module, "CONFIG_PATH", config_path)
        restored, failed = restore_saved_windows([missing_config], asset_root=state.ASSETS_DIR)
        save_config()

        saved = json.loads(config_path.read_text(encoding="utf-8"))
        assert restored == 0
        assert failed == [missing_config]
        assert saved["windows"] == [missing_config]
    finally:
        state.WINDOWS = old_windows
        state.ASSETS_DIR = old_assets_dir
        state.PRESERVED_WINDOW_CONFIGS = old_preserved
        shutil.rmtree(root)


def test_active_movement_runtime_velocity_does_not_overwrite_saved_settings(monkeypatch):
    app_instance()
    root = runtime_dir()
    old_windows = list(state.WINDOWS)
    old_control_panel = state.CONTROL_PANEL
    old_assets_dir = state.ASSETS_DIR
    old_preserved = list(state.PRESERVED_WINDOW_CONFIGS)

    class FakeClock:
        def restart(self):
            return 1000

    try:
        config_path = root / "config.json"
        state.WINDOWS = []
        state.CONTROL_PANEL = None
        monkeypatch.setattr(OverlayWindow, "visible_screen_geometry", lambda self: None)
        monkeypatch.setattr(OverlayWindow, "available_geometry", lambda self: None)

        import openanima_app.assets as assets_module

        monkeypatch.setattr(assets_module, "CONFIG_PATH", config_path)
        window = add_window(Path("icon.png").resolve(), save=False)
        assert window is not None
        window.move(10, 20)
        window.set_movement(
            {
                "enabled": True,
                "velocity_x": 42.0,
                "velocity_y": -7.0,
                "bounce": False,
                "gravity": 3.0,
                "friction": 0.5,
                "custom_parameter": 12,
            }
        )
        window.movement_clock = FakeClock()

        window.advance_movement()
        assert window.runtime_velocity_x != 42.0
        assert window.runtime_velocity_y != -7.0
        assert window.movement["velocity_x"] == 42.0
        assert window.movement["velocity_y"] == -7.0

        save_config()
        saved_movement = json.loads(config_path.read_text(encoding="utf-8"))["windows"][0]["movement"]
        assert saved_movement["enabled"] is True
        assert saved_movement["velocity_x"] == 42.0
        assert saved_movement["velocity_y"] == -7.0
        assert saved_movement["gravity"] == 3.0
        assert saved_movement["friction"] == 0.5
        assert saved_movement["custom_parameter"] == 12
    finally:
        for window in list(state.WINDOWS):
            window.stop_playback()
            window.close()
        app_instance().processEvents()
        state.WINDOWS = old_windows
        state.CONTROL_PANEL = old_control_panel
        state.ASSETS_DIR = old_assets_dir
        state.PRESERVED_WINDOW_CONFIGS = old_preserved
        shutil.rmtree(root)
