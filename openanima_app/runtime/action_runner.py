from pathlib import Path
from urllib.parse import urlparse

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices


ACTION_OPEN_FILE = "open_file"
ACTION_OPEN_FOLDER = "open_folder"
ACTION_OPEN_URL = "open_url"
ACTION_LAUNCH_APP = "launch_app"

ACTION_TYPES = {
    ACTION_OPEN_FILE,
    ACTION_OPEN_FOLDER,
    ACTION_OPEN_URL,
    ACTION_LAUNCH_APP,
}

DEFAULT_ACTION = {
    "enabled": False,
    "type": ACTION_OPEN_FILE,
    "target": "",
}


def normalized_action_config(config):
    if not isinstance(config, dict):
        return dict(DEFAULT_ACTION)

    action_type = str(config.get("type") or ACTION_OPEN_FILE)
    if action_type not in ACTION_TYPES:
        action_type = ACTION_OPEN_FILE

    normalized = {
        "enabled": bool(config.get("enabled", False)),
        "type": action_type,
        "target": str(config.get("target") or "").strip(),
    }
    for key, value in config.items():
        if key not in normalized and (isinstance(value, (str, int, float, bool)) or value is None):
            normalized[key] = value
    return normalized


class ActionRunner:
    @staticmethod
    def run(config):
        action = normalized_action_config(config)
        if not action["enabled"]:
            return False, "Action is disabled."

        target = action["target"]
        if not target:
            return False, "Choose a target before running this action."

        action_type = action["type"]
        if action_type == ACTION_OPEN_URL:
            return _open_url(target)
        if action_type == ACTION_OPEN_FOLDER:
            return _open_local_path(target, must_be_dir=True)
        if action_type in {ACTION_OPEN_FILE, ACTION_LAUNCH_APP}:
            return _open_local_path(target, must_be_dir=False)
        return False, "Unsupported action type."


def _open_url(target):
    parsed = urlparse(target)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False, "Enter a valid http or https URL."
    if not QDesktopServices.openUrl(QUrl(target)):
        return False, "The operating system could not open this URL."
    return True, ""


def _open_local_path(target, must_be_dir):
    path = Path(target).expanduser()
    if not path.exists():
        return False, "The selected path does not exist."
    if must_be_dir and not path.is_dir():
        return False, "Select a folder for this action type."
    if not must_be_dir and path.is_dir():
        return False, "Select a file or application for this action type."
    if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve()))):
        return False, "The operating system could not open this path."
    return True, ""
