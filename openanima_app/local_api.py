import json
import secrets
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from PySide6.QtCore import QObject, QPoint, QThread, Signal

from .assets.detection import detect_asset
from .assets.importer import import_asset_to_assets, import_folder_to_assets
from .assets.pack_importer import import_asset_pack
from .assets.paths import stored_path
from .assets.scanner import asset_packs, assets_for_pack, scan_assets
from .overlay import add_window, refresh_control_panel
from .runtime import recovery, state
from .runtime.action_runner import ACTION_TYPES, normalized_action_config
from .runtime.logging import log_info, log_warning
from .runtime.overlay_ids import generate_persistent_id, is_valid_persistent_id, normalize_api_alias
from .runtime.paths import SESSIONS_DIR
from .runtime.session import persist_runtime_state, serialize_overlay_window
from .version import __version__


LOCAL_API_HOST = "127.0.0.1"
DEFAULT_LOCAL_API_PORT = 8765
TOKEN_HEADER = "X-OpenAnima-Token"
SCENE_SUFFIX = ".openanima-scene.json"
EVENT_LIMIT = 100


class LocalApiDispatcher(QObject):
    submitted = Signal(object)

    def __init__(self):
        super().__init__()
        self.submitted.connect(self._run)

    def submit(self, callback):
        if QThread.currentThread() == self.thread():
            return callback()

        done = threading.Event()
        result = {"value": None, "error": None}

        def wrapped():
            try:
                result["value"] = callback()
            except Exception as exc:
                result["error"] = exc
            finally:
                done.set()

        self.submitted.emit(wrapped)
        done.wait()
        if result["error"] is not None:
            raise result["error"]
        return result["value"]

    def _run(self, callback):
        callback()


class LocalApiError(Exception):
    def __init__(self, status, code, message=None):
        if message is None:
            message = str(code).replace("_", " ")
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


class LocalApiServer:
    def __init__(self, dispatcher, token, port=DEFAULT_LOCAL_API_PORT):
        self.dispatcher = dispatcher
        self.token = token
        self.port = port
        self.httpd = None
        self.thread = None

    @property
    def url(self):
        port = self.bound_port or self.port
        return f"http://{LOCAL_API_HOST}:{port}"

    @property
    def bound_port(self):
        if self.httpd is None:
            return None
        return int(self.httpd.server_address[1])

    def start(self):
        if self.httpd is not None:
            return True

        handler = self._handler_class()
        try:
            self.httpd = ThreadingHTTPServer((LOCAL_API_HOST, self.port), handler)
        except OSError:
            self.httpd = ThreadingHTTPServer((LOCAL_API_HOST, 0), handler)

        self.thread = threading.Thread(target=self.httpd.serve_forever, name="OpenAnimaLocalApi", daemon=True)
        self.thread.start()
        log_info("Local API listening on %s", self.url)
        return True

    def stop(self):
        if self.httpd is None:
            return
        self.httpd.shutdown()
        self.httpd.server_close()
        if self.thread is not None:
            self.thread.join(timeout=2)
        log_info("Local API stopped")
        self.httpd = None
        self.thread = None

    def _handler_class(self):
        api = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "OpenAnimaLocalAPI/0.1"

            def do_GET(self):
                api.handle(self, modifying=False)

            def do_POST(self):
                api.handle(self, modifying=True)

            def log_message(self, format, *args):
                return

        return Handler

    def handle(self, request, modifying):
        try:
            if modifying:
                token = request.headers.get(TOKEN_HEADER, "")
                if not self.token or not secrets.compare_digest(token, self.token):
                    raise LocalApiError(401, "unauthorized", "Missing or invalid API token.")

            parsed = urlparse(request.path)
            path = parsed.path.rstrip("/") or "/"
            if request.command == "GET":
                result = self._handle_get(path)
            elif request.command == "POST":
                result = self._handle_post(path, self._read_json(request))
            else:
                raise LocalApiError(404, "not_found", "Endpoint not found.")
            self._send_json(request, 200, result)
        except LocalApiError as exc:
            self._send_json(request, exc.status, {"error": exc.code, "message": exc.message})
        except Exception as exc:
            log_warning("Local API internal error: %s", exc)
            record_event("error", {"message": str(exc)})
            self._send_json(request, 500, {"error": "internal_error", "message": "Unexpected internal error."})

    def _read_json(self, request):
        length_text = request.headers.get("Content-Length", "0")
        try:
            length = int(length_text)
        except ValueError:
            raise LocalApiError(400, "invalid_body", "Content-Length was invalid.")
        raw = request.rfile.read(max(0, length))
        if not raw:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise LocalApiError(400, "invalid_json", "Request body must be valid JSON.")
        if not isinstance(data, dict):
            raise LocalApiError(400, "invalid_body", "Request body must be a JSON object.")
        return data

    def _handle_get(self, path):
        if path == "/api/status":
            return {"app": "OpenAnima", "local_api": True, "version": __version__}
        if path == "/api/assets":
            return self.dispatcher.submit(list_assets)
        if path == "/api/assets/packs":
            return self.dispatcher.submit(list_asset_packs)
        if path == "/api/scenes":
            return self.dispatcher.submit(list_scenes)
        if path == "/api/events/recent":
            return recent_events()
        if path == "/api/overlays":
            return self.dispatcher.submit(list_overlays)
        if path == "/api/overlays/all":
            return self.dispatcher.submit(list_all_overlays)
        parts = path.split("/")
        if len(parts) == 5 and parts[:4] == ["", "api", "overlays", "resolve"]:
            return self.dispatcher.submit(lambda: resolve_overlay(parts[4]))
        if len(parts) == 4 and parts[:3] == ["", "api", "overlays"]:
            return self.dispatcher.submit(lambda: get_overlay(parts[3]))
        if len(parts) == 5 and parts[:3] == ["", "api", "overlays"] and parts[4] == "animations":
            return self.dispatcher.submit(lambda: overlay_animations(parts[3]))
        if len(parts) == 5 and parts[:3] == ["", "api", "overlays"] and parts[4] == "composite-values":
            return self.dispatcher.submit(lambda: get_composite_values(parts[3]))
        raise LocalApiError(404, "not_found", "Endpoint not found.")

    def _handle_post(self, path, body):
        if path == "/api/assets/import":
            return self.dispatcher.submit(lambda: import_asset_api(body))
        if path == "/api/scenes/save":
            return self.dispatcher.submit(lambda: save_scene(body))
        if path == "/api/scenes/load":
            return self.dispatcher.submit(lambda: load_scene(body))
        if path == "/api/scenes/export":
            return self.dispatcher.submit(lambda: export_scene(body))
        if path == "/api/scenes/import":
            return self.dispatcher.submit(lambda: import_scene(body))
        if path == "/api/recovery/show-all":
            return self.dispatcher.submit(lambda: recovery_action("show_all", recovery.show_all_overlays))
        if path == "/api/recovery/unlock-all":
            return self.dispatcher.submit(lambda: recovery_action("unlock_all", recovery.unlock_all_overlays))
        if path == "/api/recovery/disable-click-through-all":
            return self.dispatcher.submit(
                lambda: recovery_action("disable_click_through_all", recovery.disable_click_through_for_all)
            )
        if path == "/api/recovery/center-all":
            return self.dispatcher.submit(lambda: recovery_action("center_all", recovery.bring_all_overlays_to_center))
        if path == "/api/overlays/batch":
            return self.dispatcher.submit(lambda: batch_overlays(body))
        if path == "/api/overlays/spawn":
            return self.dispatcher.submit(lambda: spawn_overlay(body))

        parts = path.split("/")
        if len(parts) == 5 and parts[:3] == ["", "api", "overlays"]:
            overlay_id = parts[3]
            action = parts[4]
            if action == "move":
                return self.dispatcher.submit(lambda: move_overlay(overlay_id, body))
            if action == "scale":
                return self.dispatcher.submit(lambda: scale_overlay(overlay_id, body))
            if action == "opacity":
                return self.dispatcher.submit(lambda: opacity_overlay(overlay_id, body))
            if action == "speed":
                return self.dispatcher.submit(lambda: speed_overlay(overlay_id, body))
            if action == "visibility":
                return self.dispatcher.submit(lambda: visibility_overlay(overlay_id, body))
            if action == "lock":
                return self.dispatcher.submit(lambda: lock_overlay(overlay_id, body))
            if action in {"click-through", "click_through"}:
                return self.dispatcher.submit(lambda: click_through_overlay(overlay_id, body))
            if action in {"always-on-top", "always_on_top"}:
                return self.dispatcher.submit(lambda: always_on_top_overlay(overlay_id, body))
            if action == "movement":
                return self.dispatcher.submit(lambda: movement_overlay(overlay_id, body))
            if action == "action":
                return self.dispatcher.submit(lambda: action_overlay(overlay_id, body))
            if action == "update":
                return self.dispatcher.submit(lambda: update_overlay(overlay_id, body))
            if action in {"run-action", "run_action"}:
                return self.dispatcher.submit(lambda: run_action_overlay(overlay_id))
            if action == "animation":
                return self.dispatcher.submit(lambda: animation_overlay(overlay_id, body))
            if action in {"layer-value", "layer_value"}:
                return self.dispatcher.submit(lambda: layer_value_overlay(overlay_id, body))
            if action in {"layer-values", "layer_values"}:
                return self.dispatcher.submit(lambda: layer_values_overlay(overlay_id, body))
            if action in {"composite-values", "composite_values"}:
                return self.dispatcher.submit(lambda: composite_values_overlay(overlay_id, body))
            if action == "alias":
                return self.dispatcher.submit(lambda: alias_overlay(overlay_id, body))
            if action == "close":
                return self.dispatcher.submit(lambda: close_overlay(overlay_id))
        if len(parts) == 6 and parts[:3] == ["", "api", "overlays"] and parts[4] == "action" and parts[5] == "trigger":
            return self.dispatcher.submit(lambda: run_action_overlay(parts[3]))

        raise LocalApiError(404, "not_found", "Endpoint not found.")

    def _send_json(self, request, status, payload):
        content = json.dumps(payload).encode("utf-8")
        request.send_response(status)
        request.send_header("Content-Type", "application/json")
        request.send_header("Content-Length", str(len(content)))
        request.end_headers()
        request.wfile.write(content)


def ensure_dispatcher():
    if state.LOCAL_API_DISPATCHER is None:
        state.LOCAL_API_DISPATCHER = LocalApiDispatcher()
    return state.LOCAL_API_DISPATCHER


def generate_token():
    return secrets.token_urlsafe(32)


def ensure_token():
    config = dict(state.LOCAL_API_CONFIG or {})
    token = str(config.get("token") or "").strip()
    if not token:
        token = generate_token()
        config["token"] = token
        state.LOCAL_API_CONFIG = config
        persist_runtime_state("local_api_token_generated", force=True)
    return token


def set_local_api_enabled(enabled):
    config = dict(state.LOCAL_API_CONFIG or {})
    config["enabled"] = bool(enabled)
    if enabled and not str(config.get("token") or "").strip():
        config["token"] = generate_token()
    state.LOCAL_API_CONFIG = config

    if enabled:
        start_local_api()
    else:
        stop_local_api()
    persist_runtime_state("local_api_enabled_changed", force=True)


def regenerate_local_api_token():
    config = dict(state.LOCAL_API_CONFIG or {})
    config["token"] = generate_token()
    state.LOCAL_API_CONFIG = config
    if state.LOCAL_API_SERVER is not None:
        state.LOCAL_API_SERVER.token = config["token"]
    persist_runtime_state("local_api_token_regenerated", force=True)
    return config["token"]


def start_local_api():
    if state.LOCAL_API_SERVER is not None:
        return state.LOCAL_API_SERVER
    server = LocalApiServer(ensure_dispatcher(), ensure_token())
    server.start()
    state.LOCAL_API_SERVER = server
    return server


def stop_local_api():
    server = state.LOCAL_API_SERVER
    if server is not None:
        server.stop()
    state.LOCAL_API_SERVER = None


def local_api_url():
    if state.LOCAL_API_SERVER is not None:
        return state.LOCAL_API_SERVER.url
    return f"http://{LOCAL_API_HOST}:{DEFAULT_LOCAL_API_PORT}"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def record_event(event_type, payload=None):
    event = {"type": event_type, "timestamp": utc_now(), "payload": payload or {}}
    state.LOCAL_API_EVENTS.append(event)
    if len(state.LOCAL_API_EVENTS) > EVENT_LIMIT:
        del state.LOCAL_API_EVENTS[: len(state.LOCAL_API_EVENTS) - EVENT_LIMIT]
    return event


def recent_events():
    return list(state.LOCAL_API_EVENTS[-EVENT_LIMIT:])


def mark_overlay_created(window):
    state.LOCAL_API_OVERLAY_CREATED_AT.setdefault(str(id(window)), utc_now())


def asset_payload(asset, pack_name=None):
    metadata_path = Path(asset.path) / "asset.json" if Path(asset.path).is_dir() else None
    return {
        "id": asset.id,
        "name": asset.name,
        "path": str(asset.path),
        "type": asset.type,
        "pack": asset.pack or pack_name,
        "thumbnail_path": str(asset.preview_path) if asset.preview_path else None,
        "preview_path": str(asset.preview_path) if asset.preview_path else None,
        "metadata_path": str(metadata_path) if metadata_path and metadata_path.exists() else None,
        "supported": True,
    }


def list_asset_packs():
    packs = []
    for name, path in asset_packs():
        assets = assets_for_pack(path)
        packs.append({"id": name, "name": name, "path": str(path), "asset_count": len(assets)})
    return packs


def list_assets():
    assets = []
    seen = set()
    for pack_name, pack_path in asset_packs():
        for asset in assets_for_pack(pack_path):
            if asset.id in seen:
                continue
            seen.add(asset.id)
            assets.append(asset_payload(asset, pack_name=pack_name))
    return assets


def overlay_payload(window):
    pos = window.pos()
    persistent_id = str(getattr(window, "persistent_id", "") or "")
    runtime_id = str(getattr(window, "runtime_id", "") or "")
    return {
        "id": persistent_id or runtime_id or str(id(window)),
        "runtime_id": runtime_id,
        "persistent_id": persistent_id,
        "api_alias": normalize_api_alias(getattr(window, "api_alias", "")),
        "legacy_runtime_object_id": str(id(window)),
        "asset_path": str(getattr(window, "asset_path", "")),
        "asset_name": Path(getattr(window, "asset_path", "")).name,
        "asset_type": str(getattr(window, "asset_type", "")),
        "x": pos.x(),
        "y": pos.y(),
        "scale": float(getattr(window, "scale", 100)) / 100,
        "opacity": float(getattr(window, "opacity", 100)) / 100,
        "locked": bool(getattr(window, "locked", False)),
        "click_through": bool(getattr(window, "click_through", False)),
        "always_on_top": bool(getattr(window, "always_on_top", False)),
        "visible": bool(getattr(window, "intended_visible", False)),
        "speed": float(getattr(window, "speed", 100)) / 100,
        "selected_animation": getattr(window, "current_animation", None),
        "available_animations": window.available_animations() if hasattr(window, "available_animations") else [],
        "composite_values": dict(getattr(window, "layer_values", {}) or {}),
        "layer": dict(getattr(window, "layer_values", {}) or {}),
        "action": normalized_action_config(getattr(window, "action", None)),
        "movement": dict(getattr(window, "movement", {}) or {}),
        "created_at": state.LOCAL_API_OVERLAY_CREATED_AT.get(str(id(window))),
    }


def detailed_overlay_payload(window):
    payload = overlay_payload(window)
    payload.update(
        {
            "asset_type": str(getattr(window, "asset_type", "")),
            "width": window.width() if hasattr(window, "width") else None,
            "height": window.height() if hasattr(window, "height") else None,
            "visible": bool(getattr(window, "intended_visible", False)),
            "always_on_top": bool(getattr(window, "always_on_top", False)),
            "speed": float(getattr(window, "speed", 100)) / 100,
            "speed_percent": int(getattr(window, "speed", 100)),
            "current_animation": getattr(window, "current_animation", None),
            "selected_animation": getattr(window, "current_animation", None),
            "available_animations": window.available_animations() if hasattr(window, "available_animations") else [],
            "layer_values": dict(getattr(window, "layer_values", {}) or {}),
            "composite_values": dict(getattr(window, "layer_values", {}) or {}),
            "movement": dict(getattr(window, "movement", {}) or {}),
            "action": normalized_action_config(getattr(window, "action", None)),
        }
    )
    return payload


def list_overlays():
    return [overlay_payload(window) for window in state.WINDOWS]


def list_all_overlays():
    return [detailed_overlay_payload(window) for window in state.WINDOWS]


def get_overlay(overlay_id):
    return detailed_overlay_payload(find_overlay(overlay_id))


def find_overlay(overlay_id):
    needle = str(overlay_id or "")
    for window in state.WINDOWS:
        identifiers = {
            str(id(window)),
            str(getattr(window, "runtime_id", "")),
            str(getattr(window, "persistent_id", "")),
            normalize_api_alias(getattr(window, "api_alias", "")),
        }
        if needle in identifiers:
            return window
    raise LocalApiError(404, "overlay_not_found", "Overlay not found.")


def resolve_overlay(overlay_id):
    window = find_overlay(overlay_id)
    return {
        "input": str(overlay_id),
        "runtime_id": str(getattr(window, "runtime_id", "")),
        "persistent_id": str(getattr(window, "persistent_id", "")),
        "api_alias": normalize_api_alias(getattr(window, "api_alias", "")),
        "overlay": detailed_overlay_payload(window),
    }


def require_number(body, key):
    value = body.get(key)
    if isinstance(value, bool):
        raise LocalApiError(400, "invalid_parameter", f"{key} must be numeric.")
    try:
        return float(value)
    except (TypeError, ValueError):
        raise LocalApiError(400, "invalid_parameter", f"{key} must be numeric.")


def require_bool(body, key):
    if key not in body or not isinstance(body.get(key), bool):
        raise LocalApiError(400, "invalid_parameter", f"{key} must be true or false.")
    return bool(body.get(key))


def persist_and_refresh(reason):
    persist_runtime_state(reason)
    refresh_control_panel()


def require_text(body, key):
    value = body.get(key)
    if not isinstance(value, str) or not value.strip():
        raise LocalApiError(400, "invalid_parameter", f"{key} must be a non-empty string.")
    return value.strip()


def scene_name_from_body(body):
    name = require_text(body, "name")
    safe = "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in name).strip("._")
    if not safe:
        raise LocalApiError(400, "invalid_parameter", "Scene name must contain letters or numbers.")
    return safe


def scene_path(name):
    return SESSIONS_DIR / f"{name}{SCENE_SUFFIX}"


def active_persistent_ids():
    return {str(getattr(window, "persistent_id", "")) for window in state.WINDOWS if getattr(window, "persistent_id", "")}


def config_with_collision_safe_persistent_id(config, used_ids):
    config = dict(config)
    persistent_id = config.get("persistent_id")
    if not is_valid_persistent_id(persistent_id) or persistent_id in used_ids:
        persistent_id = generate_persistent_id()
        while persistent_id in used_ids:
            persistent_id = generate_persistent_id()
        config["persistent_id"] = persistent_id
    used_ids.add(persistent_id)
    return config


def normalize_api_action(action):
    mapped = dict(action)
    action_type = mapped.get("type")
    aliases = {
        "url": "open_url",
        "file": "open_file",
        "folder": "open_folder",
        "app": "launch_app",
        "application": "launch_app",
    }
    if isinstance(action_type, str):
        mapped["type"] = aliases.get(action_type, action_type)
    if mapped.get("type") not in ACTION_TYPES:
        raise LocalApiError(400, "invalid_parameter", "Unsupported action type.")
    if "enabled" not in mapped and mapped.get("target"):
        mapped["enabled"] = True
    normalized = normalized_action_config(mapped)
    if normalized["enabled"] and not normalized["target"]:
        raise LocalApiError(400, "invalid_parameter", "Action target is required when action is enabled.")
    return normalized


def ensure_composite_overlay(window):
    if str(getattr(window, "asset_type", "")) != "composite_ui":
        raise LocalApiError(400, "unsupported_feature", "This overlay is not a composite UI asset.")


def composite_layer_names(window):
    names = set()
    metadata = getattr(getattr(window, "asset", None), "metadata", None) or {}
    for layer in metadata.get("layers", []):
        if not isinstance(layer, dict):
            continue
        name = str(layer.get("name") or layer.get("image") or "").strip()
        if name:
            names.add(name)
    return names


def normalized_runtime_value(value):
    if isinstance(value, bool):
        raise LocalApiError(400, "invalid_parameter", "Composite values must be numeric.")
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        raise LocalApiError(400, "invalid_parameter", "Composite values must be numeric.")
    if 0 <= numeric <= 1:
        return numeric
    if 0 <= numeric <= 100:
        return numeric / 100
    raise LocalApiError(400, "invalid_parameter", "Composite values must be between 0 and 1 or 0 and 100.")


def apply_composite_values(window, values, require_composite):
    if require_composite:
        ensure_composite_overlay(window)
    names = composite_layer_names(window)
    for name, value in values.items():
        if not isinstance(name, str) or not name.strip():
            raise LocalApiError(400, "invalid_parameter", "Composite value names must be non-empty strings.")
        if names and name not in names:
            raise LocalApiError(400, "invalid_parameter", f"Unknown composite value: {name}")
        window.set_layer_value(name.strip(), normalized_runtime_value(value))


def spawn_overlay(body):
    asset_path = body.get("asset_path")
    if not isinstance(asset_path, str) or not asset_path.strip():
        raise LocalApiError(400, "invalid_asset_path", "asset_path must point to a supported local asset.")
    path = Path(asset_path).expanduser()
    if not path.exists():
        raise LocalApiError(400, "invalid_asset_path", "The asset path does not exist.")

    x = int(require_number(body, "x")) if "x" in body else 100
    y = int(require_number(body, "y")) if "y" in body else 100
    scale = require_number(body, "scale") if "scale" in body else 1.0
    opacity = require_number(body, "opacity") if "opacity" in body else 1.0
    if scale <= 0 or opacity < 0 or opacity > 1:
        raise LocalApiError(400, "invalid_parameter", "scale must be > 0 and opacity must be between 0 and 1.")

    config = {"x": x, "y": y, "scale": round(scale * 100), "opacity": round(opacity * 100)}
    window = add_window(path, config=config, save=True)
    if window is None:
        raise LocalApiError(400, "invalid_asset_path", "OpenAnima could not load this asset.")
    mark_overlay_created(window)
    payload = detailed_overlay_payload(window)
    record_event("overlay_created", payload)
    return payload


def move_overlay(overlay_id, body):
    window = find_overlay(overlay_id)
    x = int(require_number(body, "x"))
    y = int(require_number(body, "y"))
    window.move(window.clamped_position(QPoint(x, y)))
    persist_runtime_state("local_api_overlay_moved")
    payload = detailed_overlay_payload(window)
    record_event("overlay_moved", payload)
    return payload


def scale_overlay(overlay_id, body):
    window = find_overlay(overlay_id)
    scale = require_number(body, "scale")
    if scale <= 0:
        raise LocalApiError(400, "invalid_parameter", "scale must be greater than 0.")
    window.set_scale(round(scale * 100))
    payload = detailed_overlay_payload(window)
    record_event("overlay_updated", payload)
    return payload


def opacity_overlay(overlay_id, body):
    window = find_overlay(overlay_id)
    opacity = require_number(body, "opacity")
    if opacity < 0 or opacity > 1:
        raise LocalApiError(400, "invalid_parameter", "opacity must be between 0 and 1.")
    window.set_opacity_percent(round(opacity * 100))
    payload = detailed_overlay_payload(window)
    record_event("overlay_updated", payload)
    return payload


def speed_overlay(overlay_id, body):
    window = find_overlay(overlay_id)
    speed = require_number(body, "speed")
    if speed <= 0:
        raise LocalApiError(400, "invalid_parameter", "speed must be greater than 0.")
    window.set_speed(round(speed * 100))
    payload = detailed_overlay_payload(window)
    record_event("overlay_updated", payload)
    return payload


def visibility_overlay(overlay_id, body):
    window = find_overlay(overlay_id)
    visible = require_bool(body, "visible")
    window.set_intended_visible(visible)
    persist_and_refresh("local_api_overlay_visibility_changed")
    payload = detailed_overlay_payload(window)
    record_event("overlay_updated", payload)
    return payload


def lock_overlay(overlay_id, body):
    window = find_overlay(overlay_id)
    window.locked = require_bool(body, "locked")
    persist_and_refresh("local_api_overlay_lock_changed")
    payload = detailed_overlay_payload(window)
    record_event("overlay_updated", payload)
    return payload


def click_through_overlay(overlay_id, body):
    window = find_overlay(overlay_id)
    window.click_through = require_bool(body, "click_through")
    window.apply_click_through()
    persist_and_refresh("local_api_overlay_click_through_changed")
    payload = detailed_overlay_payload(window)
    record_event("overlay_updated", payload)
    return payload


def always_on_top_overlay(overlay_id, body):
    window = find_overlay(overlay_id)
    window.always_on_top = require_bool(body, "always_on_top")
    window.apply_window_flags()
    persist_and_refresh("local_api_overlay_always_on_top_changed")
    payload = detailed_overlay_payload(window)
    record_event("overlay_updated", payload)
    return payload


def movement_overlay(overlay_id, body):
    window = find_overlay(overlay_id)
    movement = body.get("movement", body)
    if not isinstance(movement, dict):
        raise LocalApiError(400, "invalid_body", "movement must be a JSON object.")
    merged = dict(getattr(window, "movement", {}) or {})
    merged.update(movement)
    window.set_movement(merged)
    refresh_control_panel()
    payload = detailed_overlay_payload(window)
    record_event("overlay_updated", payload)
    return payload


def action_overlay(overlay_id, body):
    window = find_overlay(overlay_id)
    action = body.get("action", body)
    if not isinstance(action, dict):
        raise LocalApiError(400, "invalid_body", "action must be a JSON object.")
    action = normalize_api_action(action)
    window.set_action(action)
    refresh_control_panel()
    payload = detailed_overlay_payload(window)
    record_event("overlay_updated", payload)
    return payload


def run_action_overlay(overlay_id):
    window = find_overlay(overlay_id)
    ok, message = window.run_action()
    record_event("overlay_updated", {"id": str(id(window)), "action_triggered": bool(ok), "message": message or ""})
    return {"ok": bool(ok), "message": message or ""}


def animation_overlay(overlay_id, body):
    window = find_overlay(overlay_id)
    animation = body.get("animation_name") or body.get("animation") or body.get("current_animation")
    if not isinstance(animation, str) or not animation.strip():
        raise LocalApiError(400, "invalid_parameter", "animation_name must be a non-empty string.")
    animations = window.available_animations() if hasattr(window, "available_animations") else []
    if not animations:
        raise LocalApiError(400, "unsupported_feature", "This overlay does not support named animations.")
    if animation.strip() not in animations:
        raise LocalApiError(400, "invalid_parameter", "The requested animation does not exist.")
    if not window.set_animation(animation.strip()):
        raise LocalApiError(409, "conflict", "OpenAnima could not switch to the requested animation.")
    refresh_control_panel()
    payload = detailed_overlay_payload(window)
    record_event("overlay_updated", payload)
    return payload


def layer_value_overlay(overlay_id, body):
    window = find_overlay(overlay_id)
    name = body.get("name") or body.get("layer")
    if not isinstance(name, str) or not name.strip():
        raise LocalApiError(400, "invalid_parameter", "Layer name must be a non-empty string.")
    value = require_number(body, "value")
    if value < 0 or value > 1:
        raise LocalApiError(400, "invalid_parameter", "Layer value must be between 0 and 1.")
    window.set_layer_value(name.strip(), value)
    refresh_control_panel()
    payload = detailed_overlay_payload(window)
    record_event("overlay_updated", payload)
    return payload


def layer_values_overlay(overlay_id, body):
    window = find_overlay(overlay_id)
    values = body.get("values", body.get("layer_values"))
    if not isinstance(values, dict):
        raise LocalApiError(400, "invalid_body", "layer values must be a JSON object.")
    apply_composite_values(window, values, require_composite=False)
    refresh_control_panel()
    payload = detailed_overlay_payload(window)
    record_event("overlay_updated", payload)
    return payload


def update_overlay(overlay_id, body):
    window = find_overlay(overlay_id)
    if "x" in body or "y" in body:
        x = int(require_number(body, "x")) if "x" in body else window.x()
        y = int(require_number(body, "y")) if "y" in body else window.y()
        window.move(window.clamped_position(QPoint(x, y)))
    if "scale" in body:
        scale = require_number(body, "scale")
        if scale <= 0:
            raise LocalApiError(400, "invalid_parameter", "scale must be greater than 0.")
        window.set_scale(round(scale * 100))
    if "opacity" in body:
        opacity = require_number(body, "opacity")
        if opacity < 0 or opacity > 1:
            raise LocalApiError(400, "invalid_parameter", "opacity must be between 0 and 1.")
        window.set_opacity_percent(round(opacity * 100))
    if "speed" in body:
        speed = require_number(body, "speed")
        if speed <= 0:
            raise LocalApiError(400, "invalid_parameter", "speed must be greater than 0.")
        window.set_speed(round(speed * 100))
    if "visible" in body:
        window.set_intended_visible(require_bool(body, "visible"))
    if "locked" in body:
        window.locked = require_bool(body, "locked")
    if "click_through" in body:
        window.click_through = require_bool(body, "click_through")
        window.apply_click_through()
    if "always_on_top" in body:
        window.always_on_top = require_bool(body, "always_on_top")
        window.apply_window_flags()
    if "movement" in body:
        if not isinstance(body["movement"], dict):
            raise LocalApiError(400, "invalid_body", "movement must be a JSON object.")
        merged = dict(getattr(window, "movement", {}) or {})
        merged.update(body["movement"])
        window.set_movement(merged)
    if "action" in body:
        if not isinstance(body["action"], dict):
            raise LocalApiError(400, "invalid_body", "action must be a JSON object.")
        window.set_action(normalize_api_action(body["action"]))
    if "animation_name" in body or "animation" in body:
        animation_overlay(overlay_id, body)
    if "composite_values" in body:
        if not isinstance(body["composite_values"], dict):
            raise LocalApiError(400, "invalid_body", "composite_values must be a JSON object.")
        apply_composite_values(window, body["composite_values"], require_composite=True)
    if "api_alias" in body:
        set_overlay_alias(window, body.get("api_alias"))
    persist_and_refresh("local_api_overlay_updated")
    payload = detailed_overlay_payload(window)
    record_event("overlay_updated", payload)
    return payload


def overlay_animations(overlay_id):
    window = find_overlay(overlay_id)
    animations = window.available_animations() if hasattr(window, "available_animations") else []
    if not animations:
        raise LocalApiError(400, "unsupported_feature", "This overlay does not support named animations.")
    return {"id": str(id(window)), "animations": animations, "selected_animation": getattr(window, "current_animation", None)}


def get_composite_values(overlay_id):
    window = find_overlay(overlay_id)
    ensure_composite_overlay(window)
    return {"id": str(id(window)), "values": dict(getattr(window, "layer_values", {}) or {})}


def composite_values_overlay(overlay_id, body):
    window = find_overlay(overlay_id)
    values = body.get("values", body.get("composite_values", body))
    if not isinstance(values, dict):
        raise LocalApiError(400, "invalid_body", "composite values must be a JSON object.")
    apply_composite_values(window, values, require_composite=True)
    refresh_control_panel()
    payload = detailed_overlay_payload(window)
    record_event("overlay_updated", payload)
    return payload


def alias_overlay(overlay_id, body):
    window = find_overlay(overlay_id)
    set_overlay_alias(window, body.get("api_alias"))
    persist_and_refresh("local_api_overlay_alias_changed")
    payload = detailed_overlay_payload(window)
    record_event("overlay_updated", payload)
    return payload


def set_overlay_alias(window, value):
    alias = normalize_api_alias(value)
    if alias:
        for other in state.WINDOWS:
            if other is not window and normalize_api_alias(getattr(other, "api_alias", "")) == alias:
                raise LocalApiError(409, "conflict", "api_alias must be unique among active overlays.")
    window.api_alias = alias


def import_asset_api(body):
    source = Path(require_text(body, "path")).expanduser().resolve()
    if not source.exists():
        raise LocalApiError(400, "invalid_parameter", "Import path does not exist.")

    imported_path = None
    pack_result = None
    if source.is_file() and source.suffix.lower() == ".zip":
        try:
            pack_result = import_asset_pack(source, state.ASSETS_DIR)
            imported_path = pack_result.path
        except Exception as exc:
            raise LocalApiError(400, "invalid_parameter", f"Asset pack import failed: {exc}")
    elif source.is_file():
        imported_path = import_asset_to_assets(source)
    elif source.is_dir() and detect_asset(source) is not None:
        imported_path = import_folder_to_assets(source)
    elif source.is_dir():
        try:
            pack_result = import_asset_pack(source, state.ASSETS_DIR)
            imported_path = pack_result.path
        except Exception as exc:
            raise LocalApiError(
                501,
                "interactive_setup_required",
                f"This folder needs interactive asset setup or is not a valid asset pack: {exc}",
            )

    if imported_path is None:
        raise LocalApiError(
            501,
            "interactive_setup_required",
            "This asset requires the interactive Asset Setup workflow before it can be imported.",
        )

    if state.CONTROL_PANEL is not None:
        state.CONTROL_PANEL.refresh_packs()
    imported_assets = scan_assets(imported_path) if Path(imported_path).is_dir() else []
    direct_asset = detect_asset(imported_path)
    if direct_asset is not None:
        imported_assets.insert(0, direct_asset)
    result = {
        "path": str(imported_path),
        "pack": pack_result.name if pack_result is not None else None,
        "assets": [asset_payload(asset) for asset in imported_assets],
    }
    record_event("asset_imported", result)
    return result


def scene_payload(name, path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    overlays = data.get("overlays", []) if isinstance(data, dict) else []
    return {"name": name, "path": str(path), "overlay_count": len(overlays), "schema_version": data.get("schema_version")}


def list_scenes():
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    scenes = []
    for path in sorted(SESSIONS_DIR.glob(f"*{SCENE_SUFFIX}"), key=lambda item: item.name.lower()):
        name = path.name[: -len(SCENE_SUFFIX)]
        scenes.append(scene_payload(name, path))
    return scenes


def current_scene_data(name):
    return {
        "schema_version": 1,
        "type": "openanima_scene",
        "name": name,
        "saved_at": utc_now(),
        "overlays": [serialize_overlay_window(window) for window in state.WINDOWS],
    }


def save_scene(body):
    name = scene_name_from_body(body)
    path = scene_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = current_scene_data(name)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    result = scene_payload(name, path)
    record_event("scene_saved", result)
    return result


def read_scene_file(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise LocalApiError(404, "scene_not_found", f"Scene file could not be read: {exc}")
    except json.JSONDecodeError:
        raise LocalApiError(400, "invalid_body", "Scene file must contain valid JSON.")
    if not isinstance(data, dict) or data.get("type") != "openanima_scene" or not isinstance(data.get("overlays"), list):
        raise LocalApiError(400, "invalid_body", "Scene file is not a valid OpenAnima scene.")
    return data


def load_scene_data(data, replace_current):
    if replace_current:
        for window in list(state.WINDOWS):
            window.close()
    used_ids = set() if replace_current else active_persistent_ids()
    loaded = []
    failed = []
    for config in data.get("overlays", []):
        if not isinstance(config, dict):
            failed.append({"error": "invalid overlay entry"})
            continue
        path_value = config.get("path") or config.get("asset_path") or config.get("gif_path")
        if not path_value:
            failed.append({"error": "missing asset path"})
            continue
        path = Path(path_value).expanduser()
        if not path.is_absolute():
            from .assets.paths import resolve_saved_asset_path

            path = resolve_saved_asset_path(path_value, asset_root=state.ASSETS_DIR)
        config = config_with_collision_safe_persistent_id(config, used_ids)
        window = add_window(path, config=config, save=False)
        if window is None:
            failed.append({"path": str(path), "error": "could not load asset"})
            continue
        mark_overlay_created(window)
        loaded.append(detailed_overlay_payload(window))
    persist_runtime_state("local_api_scene_loaded")
    refresh_control_panel()
    return {"loaded": loaded, "failed": failed}


def load_scene(body):
    name = scene_name_from_body(body)
    path = scene_path(name)
    if not path.exists():
        raise LocalApiError(404, "scene_not_found", "Scene not found.")
    data = read_scene_file(path)
    result = load_scene_data(data, bool(body.get("replace_current", True)))
    result.update(scene_payload(name, path))
    record_event("scene_loaded", result)
    return result


def export_scene(body):
    name = scene_name_from_body(body)
    path = scene_path(name)
    if not path.exists():
        raise LocalApiError(404, "scene_not_found", "Scene not found.")
    data = read_scene_file(path)
    return {"name": name, "path": str(path), "scene": data}


def import_scene(body):
    source = Path(require_text(body, "path")).expanduser().resolve()
    data = read_scene_file(source)
    name = str(data.get("name") or source.stem.replace(SCENE_SUFFIX, ""))
    safe_name = "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in name).strip("._")
    if not safe_name:
        safe_name = source.stem
    target = scene_path(safe_name)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2), encoding="utf-8")
    result = scene_payload(safe_name, target)
    if bool(body.get("replace_current", False)) or bool(body.get("load", False)):
        load_result = load_scene_data(data, bool(body.get("replace_current", False)))
        result.update(load_result)
        record_event("scene_loaded", result)
    return result


def recovery_action(name, callback):
    before = len(state.WINDOWS)
    callback()
    refresh_control_panel()
    result = {"affected_count": before, "overlays": list_all_overlays()}
    record_event("recovery_used", {"action": name, "affected_count": before})
    return result


def batch_overlays(body):
    operations = body.get("operations")
    if not isinstance(operations, list):
        raise LocalApiError(400, "invalid_body", "operations must be a list.")
    results = []
    for operation in operations:
        if not isinstance(operation, dict):
            results.append({"success": False, "status": 400, "action": None, "error": "invalid_operation"})
            continue
        action = operation.get("action")
        overlay_id = operation.get("id")
        payload = operation.get("body", operation)
        try:
            result = run_batch_operation(str(action), overlay_id, payload)
            results.append({"success": True, "status": 200, "action": action, "id": overlay_id, "result": result})
        except LocalApiError as exc:
            results.append(
                {
                    "success": False,
                    "status": exc.status,
                    "action": action,
                    "id": overlay_id,
                    "error": exc.code,
                    "message": exc.message,
                }
            )
        except Exception as exc:
            results.append(
                {"success": False, "status": 500, "action": action, "id": overlay_id, "error": "internal_error", "message": str(exc)}
            )
    return {"results": results}


def run_batch_operation(action, overlay_id, body):
    if action == "movement":
        return movement_overlay(overlay_id, body)
    if action == "action":
        return action_overlay(overlay_id, body)
    if action == "trigger_action":
        return run_action_overlay(overlay_id)
    if action == "animation":
        return animation_overlay(overlay_id, body)
    if action == "composite_values":
        return composite_values_overlay(overlay_id, body)
    if action == "alias":
        return alias_overlay(overlay_id, body)
    if action == "scene_save":
        return save_scene(body)
    if action == "scene_load":
        return load_scene(body)
    if action == "recovery_show_all":
        return recovery_action("show_all", recovery.show_all_overlays)
    if action == "recovery_unlock_all":
        return recovery_action("unlock_all", recovery.unlock_all_overlays)
    if action == "recovery_disable_click_through_all":
        return recovery_action("disable_click_through_all", recovery.disable_click_through_for_all)
    if action == "recovery_center_all":
        return recovery_action("center_all", recovery.bring_all_overlays_to_center)
    if action == "move":
        return move_overlay(overlay_id, body)
    if action == "scale":
        return scale_overlay(overlay_id, body)
    if action == "opacity":
        return opacity_overlay(overlay_id, body)
    if action == "visibility":
        return visibility_overlay(overlay_id, body)
    if action == "close":
        return close_overlay(overlay_id)
    raise LocalApiError(400, "invalid_parameter", f"Unsupported batch action: {action}")


def close_overlay(overlay_id):
    window = find_overlay(overlay_id)
    payload = detailed_overlay_payload(window)
    window.close()
    record_event("overlay_closed", payload)
    return payload
