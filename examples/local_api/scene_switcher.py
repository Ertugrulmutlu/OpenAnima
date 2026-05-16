import json
import urllib.error
import urllib.request


BASE_URL = "http://127.0.0.1:8765"
API_TOKEN = "YOUR_TOKEN"
SCENE_NAME = "coding_scene"
REPLACE_CURRENT = True


def post_json(path, body):
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-OpenAnima-Token": API_TOKEN,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"{exc.code} {detail}") from exc


def main():
    print(f"Loading scene: {SCENE_NAME}")
    print(f"replace_current: {REPLACE_CURRENT}")
    result = post_json("/api/scenes/load", {"name": SCENE_NAME, "replace_current": REPLACE_CURRENT})
    print(f"Loaded overlays: {len(result.get('loaded', []))}")
    failed = result.get("failed", [])
    if failed:
        print("Failed overlays:")
        print(json.dumps(failed, indent=2))
    else:
        print("Scene loaded successfully.")


if __name__ == "__main__":
    main()
