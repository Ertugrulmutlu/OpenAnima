# Keyboard shortcuts and overlay controls

These controls describe the current Windows app. They are contextual, not
global hotkeys; a shortcut in Asset Setup does not move a desktop overlay.

## Desktop overlays

| Input | Action |
| --- | --- |
| Left-button drag | Move an unlocked overlay, including across displays |
| Left-button double-click | Select the overlay in the existing control panel |
| **Ctrl + left-button double-click** | Run the overlay's configured action |
| Right-click | Open that overlay's context menu |

Configure actions before triggering them: they can open a local file/folder,
URL or application. Do not test with an untrusted target. Click-through overlays
do not receive these mouse events; recover them from the control panel/tray.
Locking prevents dragging. In the Inspector's **Movement / Physics** group,
configure **Enable movement**, **Velocity X/Y**, **Bounce on screen edges**,
**Gravity** and **Friction**. These are UI settings, not arrow-key bindings.

## Asset Setup: composite layer editor

Focus the layer list or preview and select a layer. Text fields, number inputs
and combo boxes retain their normal editing behaviour rather than applying the
dialog's layer shortcuts. A checked snap-to-grid option can round movement to
the 16-pixel grid.

| Keys | Action |
| --- | --- |
| Arrow keys | Nudge the selected layer 1 pixel |
| Shift + arrows | Nudge 10 pixels |
| Ctrl + arrows | Nudge 5 pixels (Shift takes precedence if both are held) |
| Ctrl + Z | Undo |
| Ctrl + Y or Ctrl + Shift + Z | Redo |
| Ctrl + C / Ctrl + V | Copy / paste a layer |
| Ctrl + D | Duplicate the selected layer |
| Delete | Remove the selected layer |
| Ctrl + ] / Ctrl + [ | Move the layer one position forward / backward |
| Ctrl + Shift + ] / Ctrl + Shift + [ | Bring to front / send to back |
| Space | Toggle the selected layer's visibility |
| F | Fit preview |
| + or = / - | Zoom in / out; Ctrl is not required by the current handler |
| Ctrl + R | Refresh the composite preview |

Drag a layer in the preview to position it. **Alt + click** or **Ctrl + click**
cycles overlapping visible layers. Save metadata to retain edits; this guide
does not add any new shortcut.

## Recover hidden, locked or off-screen overlays

Open **Settings → Recovery** and use **Show All**, **Unlock All**,
**Disable Click-Through Mode** or **Center All**, as appropriate. Center All
also shows overlays and staggers their positions; it does not unlock them or
disable click-through. **Hide All** intentionally hides overlays.
**Clear saved session** closes overlays and clears saved session state; it is
not the first recovery step.

If the panel is hidden, use the system tray's **Show Control Panel** action or
double-click the tray icon. The tray also offers show-all, disable-click-through
and bring-to-center actions. There are no dedicated global keyboard recovery
bindings in the current implementation. **Diagnostics** shows paths/logs and
copy/refresh controls; the recovery buttons are on Settings.
