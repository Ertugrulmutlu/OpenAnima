import os
import shutil
import subprocess
import sys
from pathlib import Path

from openanima_app.runtime import paths


def test_source_mode_keeps_resources_repo_local_and_runtime_data_in_appdata():
    repo_root = Path(__file__).resolve().parent.parent
    expected_data_dir = Path(os.getenv("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")) / "OpenAnima"

    assert paths.BASE_DIR == repo_root
    assert paths.BUNDLE_DIR == repo_root
    assert paths.APP_DATA_DIR == expected_data_dir
    assert paths.DEFAULT_ASSETS_DIR == expected_data_dir / "assets"
    assert paths.ASSETS_DIR == expected_data_dir / "assets"
    assert paths.BUNDLED_ASSETS_DIR == repo_root / "assets"
    assert paths.CONFIG_PATH == expected_data_dir / "config.json"
    assert paths.LOG_DIR == expected_data_dir / "logs"
    assert paths.LOG_PATH == expected_data_dir / "logs" / "openanima.log"
    assert paths.ICON_PATH == repo_root / "icon.ico"


def test_runtime_directories_are_created_under_localappdata_env():
    local_appdata = Path(".test_runtime_tmp") / "localappdata-paths"
    if local_appdata.exists():
        shutil.rmtree(local_appdata)
    local_appdata.mkdir(parents=True)

    env = os.environ.copy()
    env["LOCALAPPDATA"] = str(local_appdata.resolve())
    code = (
        "from openanima_app.runtime import paths; "
        "assert paths.APP_DATA_DIR.is_dir(); "
        "assert paths.LOG_DIR.is_dir(); "
        "assert paths.ASSETS_DIR.is_dir(); "
        "assert paths.CACHE_DIR.is_dir(); "
        "assert paths.SESSIONS_DIR.is_dir()"
    )

    try:
        subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parent.parent, env=env, check=True)
    finally:
        shutil.rmtree(local_appdata)
