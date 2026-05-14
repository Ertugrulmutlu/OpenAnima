# Changelog

All notable changes to OpenAnima will be documented in this file.

## v1.0.0

OpenAnima v1.0.0 is the first public-ready release of the Windows desktop overlay engine.

### Added

- Modular package structure under `openanima_app/` with separate assets, overlay, rendering, runtime, and UI domains.
- Overlay persistence through `config.json`, including position, scale, opacity, speed, visibility, lock state, click-through state, always-on-top state, selected spritesheet animation, composite layer values, actions, and movement settings.
- Local asset library and import workflow for files, asset folders, and asset packs.
- Asset analyzer and setup dialog for configuring metadata-driven assets.
- Desktop overlay management page and Inspector controls for selected overlays.
- Support for static images, GIF, APNG, WebM, frame-folder animations, sprite strips, spritesheets, and composite UI / HUD assets.
- Recovery tools for hidden, locked, click-through, or off-screen overlays.
- Diagnostics and rotating file logs for packaged builds.
- PyInstaller packaging readiness through `OpenAnima.spec`.

### Notes

- v1.0.0 is focused on local 2D desktop overlays for Windows.
- 3D model support is not included in v1.0.0.
- WebM playback and alpha behavior depend on the local Qt Multimedia backend and installed codecs.
- Third-party asset packs should only be used when their licenses allow it.
