# OpenAnima v1.1.0 Release Notes

OpenAnima v1.1.0 adds better multi-display overlay behavior for Windows desktop users.

## Highlights

- Multi-monitor overlay support for overlays across secondary displays.
- Monitor selection from the main UI.
- Safer overlay placement with fallback behavior when display layouts change.
- Improved runtime persistence for overlay positions and display targets.

## What’s new

- Overlays can be dragged across multiple screens instead of being restricted to the primary display.
- Monitor selection is available in the main UI so users can choose where an overlay should appear.
- If display geometry changes, overlays fall back safely to a visible screen area instead of being lost off-screen.
- Existing session persistence now includes monitor/display assignment where available.

## Notes

- This release remains Windows-focused for 2D desktop overlays.
- WebM playback depends on the local Qt Multimedia backend and installed codecs.
- APNG playback may fall back safely when the local environment lacks direct APNG support.
