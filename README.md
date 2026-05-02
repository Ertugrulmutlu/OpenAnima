# OpenAnima

<p align="center">
  <img src="icon.png" width="120" alt="OpenAnima Icon" />
</p>

<p align="center">
  <strong>Open-source desktop asset overlays for Windows.</strong>
</p>

<p align="center">
  Place GIFs, sprites, frame animations, HUD elements, and other 2D visual assets directly on your desktop.
</p>

<p align="center">
  <a href="https://ertugrulmutlu.github.io/OpenAnima/"><strong>Website</strong></a>
  |
  <a href="https://github.com/Ertugrulmutlu/OpenAnima/releases/tag/v0.2.0-preview"><strong>Latest Published Release</strong></a>
  |
  <a href="https://ertugrulmutlu.itch.io/openanima"><strong>itch.io</strong></a>
  |
  <a href="https://youtu.be/qgJBF40b_L8"><strong>Demo Video</strong></a>
</p>

---

## Release Status

OpenAnima is preparing for `v1.0.0-rc1`.

The package version is defined in `openanima_app/version.py` and exposed as:

```python
import openanima_app

print(openanima_app.__version__)
```

The current v1 release candidate focuses on reliable 2D overlays, local asset management, recovery tools, diagnostics, and safer config persistence. 3D support is not part of v1.0.

---

## What OpenAnima Does

OpenAnima is a lightweight Windows desktop app for placing local visual assets on top of your desktop as independent overlay windows.

You can use it for:

* desktop pets
* animated GIF overlays
* pixel-art characters
* sticker-like static images
* frame-folder animations
* sprite strips and spritesheets
* small HUD or game-style UI overlays
* experimental desktop customization

Each overlay can be moved, scaled, hidden, locked, made click-through, kept on top, and restored on the next launch.

---

## Quick Start

### Download

The latest published preview build is available here:

* [OpenAnima v0.2 Preview Release](https://github.com/Ertugrulmutlu/OpenAnima/releases/tag/v0.2.0-preview)
* [OpenAnima on itch.io](https://ertugrulmutlu.itch.io/openanima)

The `v1.0.0-rc1` build is being prepared.

### Run

```bash
OpenAnima.exe
```

On first launch, OpenAnima creates local runtime files such as:

```txt
assets/
config.json
logs/
```

### Add Your First Asset

1. Open the Control Panel.
2. Go to **Library**.
3. Click **Import Asset** or **Import Folder**.
4. Select a supported file or folder.
5. Review the analyzer result.
6. Confirm or configure the asset type.
7. Click **Add to Desktop**.

---

## Demo

> OpenAnima can turn your desktop into a small animated scene using game-style assets.

<p align="center">
  <a href="https://youtu.be/qgJBF40b_L8" target="_blank">
    <img src="https://img.youtube.com/vi/qgJBF40b_L8/maxresdefault.jpg" alt="OpenAnima Demo Video" width="720" />
  </a>
</p>

<p align="center">
  <a href="https://youtu.be/qgJBF40b_L8">
    Watch the demo on YouTube
  </a>
</p>

---

## Screenshots

<p align="center">
  <img src="images/DsrMR_.png" alt="OpenAnima Library tab" width="720" />
</p>

<p align="center">
  <em>Library tab for browsing imported assets, changing the asset folder, configuring assets, and adding overlays to the desktop.</em>
</p>

<p align="center">
  <img src="images/Bkmvec.png" alt="OpenAnima Active tab" width="720" />
</p>

<p align="center">
  <em>Active tab for selecting running overlays, editing them, locking/unlocking them, hiding them, or closing them.</em>
</p>

<p align="center">
  <img src="images/svkBJA.png" alt="OpenAnima Asset Setup dialog" width="720" />
</p>

<p align="center">
  <em>Asset Setup dialog for configuring metadata-driven assets such as composite UI/HUD overlays.</em>
</p>

---

## Main Features

* Multiple independent desktop overlay windows
* Drag, scale, opacity, and animation speed controls
* Lock, click-through, and always-on-top modes
* Asset library with local asset folders
* Import wizard and asset analyzer
* Metadata-driven sprite and HUD asset support
* Persistent saved sessions in `config.json`
* Safe config recovery for missing, invalid, or old configs
* Recovery actions for off-screen, hidden, locked, or click-through overlays
* File logging and a Diagnostics tab for packaged builds
* System tray controls for emergency recovery actions

---

## Supported Asset Types

### GIF

```txt
something.gif
```

GIF files are played using Qt's animation system. They support scale, opacity, speed, lock, click-through, always-on-top, and persistent position.

### Static Images

```txt
.png
.jpg
.jpeg
.webp
```

Static images are rendered as desktop overlay objects. Transparent PNGs work well for stickers, icons, characters, and decorative elements.

### Frame-Folder Animations

Frame animations can be stored as folders of ordered image files.

```txt
Idle/
  idle_01.png
  idle_02.png
  idle_03.png
```

Optional metadata:

```json
{
  "type": "frame_animation",
  "name": "Idle",
  "fps": 12
}
```

OpenAnima sorts frames naturally, so `idle_1.png`, `idle_2.png`, and `idle_10.png` play in the expected order.

### Sprite Strips

Sprite strips are single images containing multiple frames in one row or column.

```txt
Run/
  run.png
  asset.json
```

```json
{
  "name": "Run",
  "type": "sprite_strip",
  "image": "run.png",
  "frames": 8,
  "direction": "horizontal",
  "frame_width": 192,
  "frame_height": 192,
  "fps": 8,
  "loop": true
}
```

Sprite strip setup supports horizontal and vertical strips, frame count, FPS, loop mode, explicit frame size, crop margins, live preview, and frame export.

### Spritesheets

Spritesheets can define named animations using metadata.

```txt
Slime/
  sheet.png
  asset.json
```

```json
{
  "name": "Slime",
  "type": "spritesheet",
  "image": "sheet.png",
  "frame_width": 32,
  "frame_height": 32,
  "default_animation": "idle",
  "animations": {
    "idle": {
      "fps": 8,
      "loop": true,
      "frames": [
        { "col": 0, "row": 0 },
        { "col": 1, "row": 0 },
        { "x": 64, "y": 0 }
      ]
    }
  }
}
```

Supported spritesheet features include named animations, default animation, `col` / `row` frame definitions, direct `x` / `y` frame definitions, animation-specific FPS, animation selection in the editor, and per-overlay animation persistence.

### Composite UI / HUD Assets

Composite UI assets are made from multiple image layers. They are useful for HUD-style elements such as health bars, mana bars, stamina bars, energy bars, status panels, and layered UI widgets.

```txt
HP Bar/
  Hp bar.png
  red bar.png
  Blue bar.png
  yellow bar.png
  HP bar preview.png
  asset.json
```

```json
{
  "name": "Sci-Fi HP Bar",
  "type": "composite_ui",
  "preview": "HP bar preview.png",
  "layers": [
    {
      "name": "base",
      "image": "Hp bar.png",
      "x": 0,
      "y": 0
    },
    {
      "name": "health",
      "image": "red bar.png",
      "x": 380,
      "y": 324,
      "value": 1.0,
      "clip": "horizontal"
    }
  ]
}
```

Composite layers support image paths, x/y position, visibility, opacity, horizontal clipping, vertical clipping, and runtime values. Runtime values are saved per overlay without overwriting the original `asset.json`.

---

## Feature Status

| Area | Status | Notes |
| --- | --- | --- |
| GIF overlays | Stable | Core workflow for animated desktop overlays. |
| Static image overlays | Stable | Good for transparent PNGs and sticker-like assets. |
| Frame-folder animations | Stable | Uses ordered local image files and optional FPS metadata. |
| Overlay transform controls | Stable | Move, scale, opacity, speed, lock, click-through, and always-on-top. |
| Session persistence | Stable | Saved to `config.json` with schema versioning and safe recovery. |
| Recovery tools | Stable | Center overlays, show/hide all, unlock all, disable click-through, and clear session. |
| Diagnostics and logs | Stable | `logs/openanima.log` plus Diagnostics tab. |
| Asset import analyzer | Beta | Helps classify assets, but ambiguous packs may still need manual setup. |
| Sprite strip setup | Beta | Functional; unusual padding or frame layouts may need manual crop values. |
| Spritesheet metadata | Beta | Works with explicit metadata; automatic detection is limited. |
| Composite UI / HUD overlays | Beta | Useful for layered HUD assets; editor is not a full design tool. |
| Metadata reload for running overlays | Beta | Reloads many changes safely, but some invalid changes are rejected. |
| Complex third-party asset packs | Known limitation | Licensing and inconsistent folder formats may require manual cleanup. |
| 3D model support | Experimental after v1.0 | Planned research area; not included in v1.0. |
| Cross-platform support | Known limitation | v1.0 is focused on Windows. |

---

## Control Panel

### Library

Use the Library tab to browse asset packs, import files or folders, run the asset analyzer, configure metadata-driven assets, and add overlays to the desktop.

### Active

Use the Active tab to view running overlays, select overlays, close overlays, edit overlay state, and access recovery tools.

### Editor

Use the Editor tab to fine-tune selected overlays:

* scale
* opacity
* speed
* lock / unlock
* click-through
* always-on-top
* reload asset
* spritesheet animation selection
* composite UI runtime sliders

### Diagnostics

Use the Diagnostics tab to inspect:

* OpenAnima version
* config path
* current asset root
* log file path
* active overlay count
* recent warnings and errors

The tab also includes buttons to open the logs folder and copy diagnostic info to the clipboard.

---

## Recovery and Reset Tools

OpenAnima includes recovery actions so users can regain control if overlays are hidden, locked, click-through, or off-screen.

Available from the **Active** tab:

* **Bring all to center**: moves active overlays to the center of the primary screen.
* **Disable click-through**: makes every active overlay interactive again.
* **Unlock all**: unlocks every active overlay.
* **Show all**: shows hidden overlays.
* **Hide all**: hides active overlays.
* **Clear saved session**: closes active overlays and saves an empty overlay session after confirmation.

Available from the system tray menu:

* **Show Control Panel**
* **Show all overlays**
* **Disable click-through for all**
* **Bring all overlays to center**
* **Exit**

---

## Diagnostics and Logs

OpenAnima writes logs to:

```txt
logs/openanima.log
```

Logs use Python's standard logging system with rotation. They are useful when running a packaged build without a terminal.

Logged events include:

* app startup and shutdown
* config load/save warnings
* corrupt config backup
* missing saved assets
* unsupported asset imports
* metadata validation warnings
* overlay creation, removal, and reload events
* recovery actions

If logging setup fails, OpenAnima should still start.

---

## Configuration and Persistence

OpenAnima stores runtime state in:

```txt
config.json
```

Saved state includes:

* asset root
* schema version
* active overlay list
* asset paths and asset types
* position
* scale
* opacity
* speed
* lock state
* click-through state
* always-on-top state
* selected spritesheet animation
* composite UI runtime values

Config saves are atomic: OpenAnima writes a temporary file first, then replaces `config.json`.

If `config.json` is corrupted, OpenAnima backs it up as:

```txt
config.corrupt.YYYYMMDD_HHMMSS.json
```

The app then starts with safe defaults instead of crashing.

If saved overlays point to missing assets, those overlays are skipped while valid saved overlays continue to load.

---

## Asset Folder Structure

Simple assets can be placed directly inside `assets/`.

```txt
assets/
  cat.gif
  sticker.png
```

Metadata-driven assets can use folders.

```txt
assets/
  Archer_Run/
    Archer_Run.png
    asset.json

  HP_Bar/
    Hp bar.png
    red bar.png
    Blue bar.png
    asset.json
```

---

## Known Limitations

* v1.0 is focused on 2D overlays for Windows.
* 3D model support is not included in v1.0.
* Sprite strips may require manual frame count, frame size, or crop correction.
* Spritesheets require metadata or setup through the import wizard.
* Composite UI assets may require manual layer alignment.
* The Composite UI editor is functional but not a professional layout tool.
* Some unusual asset packs may still need manual `asset.json` editing.
* Third-party asset packs should only be used if their license allows it.
* Cross-platform behavior is not a v1.0 guarantee.

---

## Roadmap After v1.0

Possible post-v1 improvements:

* better sprite crop and anchor tools
* improved composite UI editor
* asset pack export/import
* plugin or extension hooks
* advanced animation behaviors
* scene presets
* improved diagnostics export
* cross-platform investigation
* experimental 3D model support with `.glb` / `.gltf`

3D support is planned as experimental research after v1.0, not as part of the v1 release candidate.

---

## Build From Source

```bash
pip install -r requirements.txt
python main.py
```

---

## Build EXE

```bash
pyinstaller OpenAnima.spec
```

Output:

```txt
dist/OpenAnima.exe
```

The spec bundles `icon.ico`, `icon.png`, `assets/`, `images/`, `README.md`, and `LICENSE`. Runtime files such as `config.json` and `logs/` are created beside the executable.

---

## Tech Stack

* Python
* PySide6 / Qt
* PyInstaller
* JSON-based asset metadata
* Local asset folders

---

## Links

* Website: [https://ertugrulmutlu.github.io/OpenAnima/](https://ertugrulmutlu.github.io/OpenAnima/)
* GitHub: [https://github.com/Ertugrulmutlu/OpenAnima](https://github.com/Ertugrulmutlu/OpenAnima)
* Latest published release: [https://github.com/Ertugrulmutlu/OpenAnima/releases/tag/v0.2.0-preview](https://github.com/Ertugrulmutlu/OpenAnima/releases/tag/v0.2.0-preview)
* itch.io: [https://ertugrulmutlu.itch.io/openanima](https://ertugrulmutlu.itch.io/openanima)
* Demo video: [https://youtu.be/qgJBF40b_L8](https://youtu.be/qgJBF40b_L8)

---

## Contributing

Contributions are welcome. Good v1-focused contributions include:

* bug reports
* recovery and reliability testing
* testing asset packs
* improving import detection
* documentation fixes
* focused pull requests

See [CONTRIBUTING.md](CONTRIBUTING.md) for basic contributor guidance.

---

## License

MIT License. See [LICENSE](LICENSE).

---

Built by Ertugrul Mutlu.
