from pathlib import Path

from openanima_app import constants


def test_source_mode_paths_are_repo_local():
    repo_root = Path(__file__).resolve().parent.parent

    assert constants.BASE_DIR == repo_root
    assert constants.BUNDLE_DIR == repo_root
    assert constants.DEFAULT_ASSETS_DIR == repo_root / "assets"
    assert constants.BUNDLED_ASSETS_DIR == repo_root / "assets"
    assert constants.CONFIG_PATH == repo_root / "config.json"
    assert constants.LOG_DIR == repo_root / "logs"
    assert constants.LOG_PATH == repo_root / "logs" / "openanima.log"
    assert constants.ICON_PATH == repo_root / "icon.ico"
