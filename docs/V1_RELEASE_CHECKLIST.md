# OpenAnima v1 Release Checklist

## Repository Hygiene

- Confirm `.gitignore` excludes local virtual environments, Python caches, build outputs, PyInstaller artifacts, local configuration, and Windows binaries.
- Remove generated artifacts from git tracking if they were committed previously.
- Check `git status --short` before preparing the release branch.
- Verify `config.json` recovery by testing missing, corrupt, partial, and old-schema configs.
- Confirm `logs/openanima.log` is created and receives startup, shutdown, config, asset, and overlay warnings.

## Version And Metadata

- Confirm `openanima_app.version.__version__` is set to the release version.
- Confirm `openanima_app.__version__` imports without starting the GUI.
- Update `CHANGELOG.md` for the release.
- Confirm `LICENSE` is present and correct.

## Local Validation

- Install dependencies in a clean virtual environment.
- Run `python -c "import openanima_app; print(openanima_app.__version__)"`.
- Run available tests or checks.
- Launch the app with `python main.py` and smoke test core desktop overlay workflows.
- Corrupt a temporary copy of `config.json` and confirm OpenAnima starts with defaults while preserving a `config.corrupt.*.json` backup.
- Open the Diagnostics tab, verify paths and active overlay count, open the logs folder, and copy diagnostic info to the clipboard.

## Packaging

- Build the Windows app from a clean checkout.
- Verify the generated executable launches on a clean Windows environment.
- Confirm bundled assets, icons, and docs are present.
- Confirm no local `config.json`, caches, or temporary files are included in the distributable.

## Release

- Create a release commit and tag.
- Upload release artifacts and checksums.
- Publish release notes from `CHANGELOG.md`.
- Verify GitHub release links, website links, and itch.io links point to the v1 release.
