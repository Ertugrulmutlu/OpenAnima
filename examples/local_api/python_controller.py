import json
import os
import urllib.error
import urllib.request


BASE_URL = "http://127.0.0.1:8765"
API_TOKEN = "YOUR_TOKEN"
ASSET_PATH = ""


def request_json(method, path, body=None, token_required=False):
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token_required:
        headers["X-OpenAnima-Token"] = API_TOKEN

    request = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"{exc.code} {detail}") from exc


def get_json(path):
    return request_json("GET", path)


def post_json(path, body=None):
    return request_json("POST", path, body=body or {}, token_required=True)


def main():
    print("Status")
    print(json.dumps(get_json("/api/status"), indent=2))

    print("\nCurrent overlays")
    overlays = get_json("/api/overlays/all")
    print(json.dumps(overlays, indent=2))

    overlay = None
    if ASSET_PATH and os.path.exists(ASSET_PATH):
        print("\nSpawning overlay")
        overlay = post_json(
            "/api/overlays/spawn",
            {"asset_path": ASSET_PATH, "x": 200, "y": 200, "scale": 1.0, "opacity": 1.0},
        )
        print(json.dumps(overlay, indent=2))
    elif overlays:
        overlay = overlays[0]

    if not overlay:
        print("\nNo overlay available. Set ASSET_PATH to spawn one.")
        return

    overlay_id = overlay["persistent_id"]
    print(f"\nUsing overlay {overlay_id}")

    post_json(f"/api/overlays/{overlay_id}/move", {"x": 320, "y": 260})
    post_json(f"/api/overlays/{overlay_id}/scale", {"scale": 1.2})
    post_json(f"/api/overlays/{overlay_id}/opacity", {"opacity": 0.8})
    updated = post_json(f"/api/overlays/{overlay_id}/alias", {"api_alias": "python_demo"})
    print(json.dumps(updated, indent=2))

    print("\nSaving scene")
    print(json.dumps(post_json("/api/scenes/save", {"name": "python_demo_scene"}), indent=2))

    print("\nRecent events")
    print(json.dumps(get_json("/api/events/recent")[-10:], indent=2))


if __name__ == "__main__":
    main()
