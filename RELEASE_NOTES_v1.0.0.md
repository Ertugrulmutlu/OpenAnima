# OpenAnima v1.0.0 Release Notes

OpenAnima v1.0.0 is the first public-ready release of the open-source Windows desktop overlay engine.

OpenAnima lets users place local 2D visual assets on the desktop as independent transparent overlay windows. It is designed for desktop pets, animated GIF overlays, pixel-art characters, stickers, sprite animations, HUD-style widgets, and local desktop customization.

## Highlights

- Packaged Windows desktop overlay app.
- Multiple independent overlay windows.
- Move, scale, opacity, speed, lock, click-through, always-on-top, show/hide, and remove controls.
- Persistent sessions saved to `config.json`.
- Safer config persistence with schema versioning, atomic writes, and corrupt-config backup.
- Local Library workflow for importing files, folders, and asset packs.
- Asset analyzer and setup dialog for metadata-driven assets.
- Inspector controls for selected overlays.
- Optional per-overlay actions for opening files, folders, URLs, or applications.
- Optional movement settings with velocity, bounce, gravity, and friction.
- Recovery tools for overlays that are hidden, locked, click-through, or off-screen.
- Diagnostics page and rotating file logs.
- PyInstaller build configuration through `OpenAnima.spec`.

## Supported Assets

- Static images: `.png`, `.jpg`, `.jpeg`, `.webp`
- GIF animations
- APNG animations, with safe fallback when animation decoding is unavailable
- WebM video overlays through Qt Multimedia
- Frame-folder animations
- Sprite strips
- Spritesheets with metadata-defined animations
- Composite UI / HUD-style layered assets

## Known Limitations

- v1.0.0 is focused on Windows.
- v1.0.0 is focused on 2D overlays; 3D model support is not included.
- APNG support depends on available decoding support and may fall back.
- WebM playback depends on Qt Multimedia, installed codecs, and backend behavior.
- Transparent WebM alpha is backend-dependent and may not be preserved.
- Sprite strips and spritesheets may require manual metadata or crop correction.
- Composite UI assets may require manual layer alignment.
- Some third-party asset packs may require manual cleanup before import.
- Users should only include or redistribute assets they have rights to use.

## Manual Test Checklist

- Launch `OpenAnima.exe`.
- Confirm the Control Panel opens cleanly.
- Import and add a static image.
- Import and add a GIF.
- Import and add an APNG and confirm safe display or playback.
- Import and add a WebM on a machine with suitable codec support.
- Import and add a frame-folder animation.
- Configure and add a sprite strip.
- Configure and add a spritesheet with a named animation.
- Configure and add a composite UI asset and adjust a runtime layer value.
- Move, scale, change opacity, and change speed on an overlay.
- Toggle lock, click-through, always-on-top, visible, and hidden states.
- Restart the app and confirm valid overlays restore.
- Confirm missing saved assets are skipped without crashing.
- Use recovery actions: center all, show all, unlock all, disable click-through.
- Confirm `logs/openanima.log` is created.
- Confirm Diagnostics shows version, config path, asset root, log path, active overlay count, and recent warnings.
- Run `pyinstaller OpenAnima.spec` and test the packaged executable.

## Build

```bash
pyinstaller OpenAnima.spec
```

Expected release output for a folder-style build:

```txt
dist/OpenAnima/OpenAnima.exe
```

Depending on the PyInstaller mode emitted by the current spec, local builds may also produce:

```txt
dist/OpenAnima.exe
```

The spec uses `icon.ico` for the executable icon.
