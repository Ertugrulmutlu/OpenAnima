# OpenAnima

<p align="center">
  <img src="icon.png" width="120" alt="OpenAnima Icon" />
</p>

<p align="center">
  <strong>Open-source desktop overlay engine for Windows.</strong>
</p>

<p align="center">
  Place local GIFs, images, sprites, frame animations, videos, and HUD-style 2D assets directly on your desktop.
</p>

<p align="center">
  <a href="https://ertugrulmutlu.github.io/OpenAnima/"><strong>Website</strong></a>
  |
  <a href="https://github.com/Ertugrulmutlu/OpenAnima/releases"><strong>Releases</strong></a>
  |
  <a href="https://ertugrulmutlu.itch.io/openanima"><strong>itch.io</strong></a>
  |
  <a href="https://youtu.be/qgJBF40b_L8"><strong>Demo Video</strong></a>
</p>

---

## Overview

OpenAnima is a lightweight Windows desktop app for running local 2D visual assets as independent overlay windows. It is built for desktop pets, animated GIF overlays, pixel-art characters, sticker-like images, sprite animations, small HUD widgets, and experimental desktop customization.

Each overlay can be moved, scaled, hidden, locked, made click-through, kept on top, and restored on the next launch. OpenAnima stores its runtime state locally and does not require an online service.

The package version is defined in `openanima_app/version.py` and exposed as:

```python
import openanima_app

print(openanima_app.__version__)
```

## Features

- Multiple independent transparent desktop overlay windows.
- Drag, scale, opacity, and animation speed controls.
- Lock, click-through, always-on-top, show/hide, and remove controls.
- Local asset library with import workflows for files, folders, and asset packs.
- Asset analyzer and setup dialog for configuring metadata-driven assets.
- Inspector controls for selected overlays.
- Optional per-overlay actions for opening files, folders, URLs, or applications.
- Optional movement settings with velocity, screen-edge bounce, gravity, and friction.
- Persistent sessions saved to `config.json`.
- Safer config loading with schema versioning, atomic writes, and corrupt-config backup.
- Recovery tools for hidden, locked, click-through, or off-screen overlays.
- System tray recovery actions.
- File logging in `logs/openanima.log`.
- Diagnostics page for packaged builds.

## Supported Asset Types

| Asset type | Status | Notes |
| --- | --- | --- |
| GIF | Supported | Animated with Qt movie playback. |
| Static images | Supported | `.png`, `.jpg`, `.jpeg`, and `.webp`. Transparent PNGs work well. |
| APNG | Supported with fallback | APNG frames are decoded when available; unreadable animation falls back safely. |
| WebM | Supported | Playback uses Qt Multimedia. Codec and alpha behavior depend on the system backend. |
| Frame folders | Supported | Ordered image frames with optional `asset.json` metadata. |
| Sprite strips | Supported | Single-row or single-column sprite strips with frame settings. |
| Spritesheets | Supported with metadata | Named animations are configured in `asset.json`. |
| Composite UI / HUD | Supported with metadata | Layered image assets with runtime value sliders. |

Example frame-folder asset:

```txt
Idle/
  idle_01.png
  idle_02.png
  idle_03.png
  asset.json
```

Example `asset.json`:

```json
{
  "type": "frame_animation",
  "name": "Idle",
  "fps": 12
}
```

## Demo And Screenshots

Demo video:

[Watch OpenAnima on YouTube](https://youtu.be/qgJBF40b_L8)

Screenshot placeholders:

```txt
docs/images/DsrMR_.png       Library page
docs/images/Bkmvec.png       Desktop / active overlays page
docs/images/svkBJA.png       Asset setup dialog
docs/images/diagnostic.png   Diagnostics page
```

The website assets in `docs/images/` can be refreshed before publishing if newer screenshots are available.

## Install And Run

### Download

Download the Windows build from the GitHub Releases page:

```txt
https://github.com/Ertugrulmutlu/OpenAnima/releases
```

Run:

```bash
OpenAnima.exe
```

On first launch, OpenAnima creates local runtime files beside the executable or source checkout:

```txt
assets/
config.json
logs/
```

### Run From Source

Requirements:

- Windows
- Python 3.11 or newer recommended
- Dependencies from `requirements.txt`

```bash
pip install -r requirements.txt
python main.py
```

## Basic Usage

1. Open the Control Panel.
2. Go to **Library**.
3. Click **Import Asset**, **Import Asset Folder**, or **Import Asset Pack**.
4. Review the detected type in the Asset Setup dialog.
5. Confirm the metadata or choose a manual type.
6. Select the imported asset and click **Add to Desktop**.
7. Use the **Desktop** page and Inspector to edit the overlay.

## Build EXE

OpenAnima uses PyInstaller and `OpenAnima.spec`.

```bash
pyinstaller OpenAnima.spec
```

Expected release output for a folder-style PyInstaller build:

```txt
dist/OpenAnima/OpenAnima.exe
```

The current spec is configured with `icon.ico`:

```python
icon=['icon.ico']
```

Depending on the PyInstaller mode produced by the spec, local builds may also emit a single executable at:

```txt
dist/OpenAnima.exe
```

Runtime files such as `config.json`, `assets/`, and `logs/` are created or used next to the running application.

## Project Structure

```txt
OpenAnima/
  main.py                    Application entry point
  OpenAnima.spec             PyInstaller build configuration
  requirements.txt           Python dependencies
  README.md                  Project documentation
  CHANGELOG.md               Release history
  LICENSE                    MIT license
  NOTICE.md                  Asset and rights notice
  docs/                      Website and release materials
  assets/                    Local sample/runtime asset folder
  tests/                     Automated tests
  openanima_app/
    app.py                   Application startup and tray wiring
    version.py               Package version
    assets/                  Asset models, metadata, detection, import, scan, thumbnails
    overlay/                 Overlay windows, flags, menus, movement, serialization
    rendering/               GIF/APNG/video/frame/sprite/composite rendering helpers
    runtime/                 Paths, logging, config, session, recovery, state, actions
    ui/
      asset_setup/           Asset setup dialog and preview helpers
      control_panel/         Library, Desktop, Editor, Settings, Diagnostics, About pages
```

## Configuration And Persistence

OpenAnima stores session state in:

```txt
config.json
```

Saved state includes asset root, active overlays, asset paths and types, position, scale, opacity, speed, lock state, click-through state, always-on-top state, visibility, selected spritesheet animation, composite UI runtime values, per-overlay actions, and movement settings.

Config saves are atomic. If `config.json` is corrupted, OpenAnima backs it up as:

```txt
config.corrupt.YYYYMMDD_HHMMSS.json
```

The app then starts with safe defaults. Missing saved assets are skipped without preventing valid overlays from loading.

## Manual Smoke-Test Checklist

Before publishing a v1 release, run this checklist on a clean Windows machine or clean test folder:

- Launch `OpenAnima.exe`.
- Confirm the Control Panel opens without a terminal.
- Import a static PNG or JPG and add it to the desktop.
- Import a GIF and confirm it animates.
- Import an APNG and confirm it displays or falls back safely.
- Import a WebM and confirm playback starts when system codecs support it.
- Import a frame-folder animation.
- Import or configure a sprite strip.
- Import or configure a spritesheet with at least one named animation.
- Import or configure a composite UI asset and move a runtime value slider.
- Move, scale, change opacity, and change speed on an overlay.
- Toggle lock, click-through, always-on-top, visible, and hidden states.
- Restart the app and confirm valid overlays restore from `config.json`.
- Confirm missing saved assets are skipped without crashing.
- Use recovery actions: center all, show all, unlock all, disable click-through.
- Confirm `logs/openanima.log` is created and Diagnostics shows useful paths.
- Build with `pyinstaller OpenAnima.spec` and run the packaged executable.

## Known Limitations

- v1 is focused on 2D overlays for Windows.
- 3D model support is not included in v1.
- APNG playback depends on available decoding support and may fall back.
- WebM playback depends on Qt Multimedia, installed codecs, and backend behavior.
- Transparent WebM alpha is backend-dependent and may not be preserved.
- Sprite strips and spritesheets may require manual metadata or crop correction.
- Composite UI assets may require manual layer alignment.
- Third-party asset packs vary in structure and may need cleanup.
- Cross-platform behavior is not a v1 guarantee.

## Credits And Asset Disclaimer

OpenAnima itself is the desktop overlay engine. Sample, demo, or third-party assets included in screenshots, tests, local asset folders, or demos may belong to their original creators.

Only include, redistribute, or publish assets that you have the rights to use. See [NOTICE.md](NOTICE.md) for the repository notice.

Built by Ertugrul Mutlu.

## License

OpenAnima is released under the MIT License. See [LICENSE](LICENSE).
