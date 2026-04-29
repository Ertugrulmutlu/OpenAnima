import os
import subprocess
import sys
from pathlib import Path

from .constants import BASE_DIR


APP_NAME = "OpenAnima"


def startup_shortcut_path():
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / f"{APP_NAME}.lnk"


def startup_enabled():
    shortcut = startup_shortcut_path()
    return bool(shortcut and shortcut.exists())


def set_startup_enabled(enabled):
    if sys.platform != "win32":
        return

    shortcut = startup_shortcut_path()
    if shortcut is None:
        return

    if not enabled:
        if shortcut.exists():
            shortcut.unlink()
        return

    shortcut.parent.mkdir(parents=True, exist_ok=True)
    target = Path(sys.executable).resolve()
    script = BASE_DIR / "main.py"
    command = (
        "$shell = New-Object -ComObject WScript.Shell; "
        f"$shortcut = $shell.CreateShortcut('{shortcut}'); "
        f"$shortcut.TargetPath = '{target}'; "
        f"$shortcut.Arguments = '\"{script}\"'; "
        f"$shortcut.WorkingDirectory = '{BASE_DIR}'; "
        "$shortcut.Save()"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
