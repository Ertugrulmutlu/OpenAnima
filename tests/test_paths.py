from pathlib import Path

from openanima_app.runtime import paths


def test_source_mode_paths_are_repo_local():
    repo_root = Path(__file__).resolve().parent.parent

    assert paths.BASE_DIR == repo_root
    assert paths.BUNDLE_DIR == repo_root
    assert paths.DEFAULT_ASSETS_DIR == repo_root / "assets"
    assert paths.BUNDLED_ASSETS_DIR == repo_root / "assets"
    assert paths.CONFIG_PATH == repo_root / "config.json"
    assert paths.LOG_DIR == repo_root / "logs"
    assert paths.LOG_PATH == repo_root / "logs" / "openanima.log"
    assert paths.ICON_PATH == repo_root / "icon.ico"
