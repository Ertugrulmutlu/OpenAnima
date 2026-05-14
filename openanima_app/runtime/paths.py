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

DEFAULT_ASSETS_DIR = BASE_DIR / "assets"
BUNDLED_ASSETS_DIR = resource_path("assets")
CONFIG_PATH = BASE_DIR / "config.json"
LOG_DIR = BASE_DIR / "logs"
LOG_PATH = LOG_DIR / "openanima.log"
DEFAULT_GIF = BASE_DIR / "overlay.gif"
ICON_PATH = resource_path("icon.ico")
