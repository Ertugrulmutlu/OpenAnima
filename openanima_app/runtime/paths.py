import os
import sys
from pathlib import Path


def resource_path(relative_path):
    if getattr(sys, "frozen", False):
        base_path = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base_path = Path(__file__).resolve().parent.parent.parent

    return base_path / relative_path


BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent.parent))

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

_LOCALAPPDATA = os.getenv("LOCALAPPDATA")
if _LOCALAPPDATA:
    APP_DATA_DIR = Path(_LOCALAPPDATA) / "OpenAnima"
else:
    APP_DATA_DIR = Path.home() / "AppData" / "Local" / "OpenAnima"

LOG_DIR = APP_DATA_DIR / "logs"
ASSETS_DIR = APP_DATA_DIR / "assets"
CACHE_DIR = APP_DATA_DIR / "cache"
SESSIONS_DIR = APP_DATA_DIR / "sessions"
CONFIG_PATH = APP_DATA_DIR / "config.json"
LOG_PATH = LOG_DIR / "openanima.log"

for _directory in (APP_DATA_DIR, LOG_DIR, ASSETS_DIR, CACHE_DIR, SESSIONS_DIR):
    try:
        _directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"OpenAnima warning: could not create runtime directory {_directory}: {exc}")

DEFAULT_ASSETS_DIR = ASSETS_DIR
BUNDLED_ASSETS_DIR = resource_path("assets")
DEFAULT_GIF = BASE_DIR / "overlay.gif"
ICON_PATH = resource_path("icon.ico")
