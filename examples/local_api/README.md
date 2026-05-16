# OpenAnima Local API Examples And Reference

OpenAnima's experimental Local API lets same-machine automation tools control overlays, assets, scenes, recovery actions, and local event history. It is designed for streamer tools, VTuber setups, OBS helper scripts, and desktop automation utilities.

## Enable The API

1. Start OpenAnima.
2. Open the **Local API** page in the Control Panel.
3. Turn on **Enable Local API**.
4. Click **Regenerate Token** if no token exists.
5. Click **Copy Base URL** and **Copy API Token**.

The API is disabled by default and binds only to `127.0.0.1`. Do not proxy or expose it to LAN or public networks.

## Token Usage

Every modifying `POST` request must include:

```txt
X-OpenAnima-Token: YOUR_TOKEN
```

PowerShell setup:

```powershell
$base = "http://127.0.0.1:8765"
$token = "YOUR_TOKEN"
$headers = @{ "X-OpenAnima-Token" = $token }
```

## Overlay IDs

OpenAnima exposes multiple identifiers:

* `persistent_id`: stable across restarts when an overlay is saved/restored. External tools should prefer this.
* `runtime_id`: stable only for the current app session.
* `api_alias`: optional user-friendly name, such as `main_cat`.
* `id`: public Local API ID. This currently maps to `persistent_id`.

Overlay endpoints accept `persistent_id`, `runtime_id`, legacy object ID, or `api_alias`.

## Status

```powershell
Invoke-RestMethod -Uri "$base/api/status" -Method Get
```

## Assets, Packs, And Import

```powershell
Invoke-RestMethod -Uri "$base/api/assets" -Method Get
Invoke-RestMethod -Uri "$base/api/assets/packs" -Method Get
```

Import a supported asset file, folder asset, folder pack, or `.zip` pack:

```powershell
$body = @{ path = "C:/path/to/asset-or-pack" } | ConvertTo-Json
Invoke-RestMethod -Uri "$base/api/assets/import" -Method Post -Headers $headers -ContentType "application/json" -Body $body
```

If a path needs OpenAnima's interactive Asset Setup workflow, the API returns `501 interactive_setup_required`.

## Overlays And Resolve

```powershell
$overlays = @(Invoke-RestMethod -Uri "$base/api/overlays/all" -Method Get)
$overlays | Format-Table id, runtime_id, persistent_id, api_alias, asset_name

$id = $overlays[0].persistent_id
Invoke-RestMethod -Uri "$base/api/overlays/$id" -Method Get
Invoke-RestMethod -Uri "$base/api/overlays/resolve/$id" -Method Get
```

## Spawn, Move, Scale, Opacity, Update

Spawn:

```powershell
$body = @{
  asset_path = "C:/path/to/asset.gif"
  x = 200
  y = 200
  scale = 1.0
  opacity = 1.0
} | ConvertTo-Json

$overlay = Invoke-RestMethod -Uri "$base/api/overlays/spawn" -Method Post -Headers $headers -ContentType "application/json" -Body $body
$id = $overlay.persistent_id
```

Move, scale, and opacity:

```powershell
$body = @{ x = 300; y = 400 } | ConvertTo-Json
Invoke-RestMethod -Uri "$base/api/overlays/$id/move" -Method Post -Headers $headers -ContentType "application/json" -Body $body

$body = @{ scale = 1.25 } | ConvertTo-Json
Invoke-RestMethod -Uri "$base/api/overlays/$id/scale" -Method Post -Headers $headers -ContentType "application/json" -Body $body

$body = @{ opacity = 0.8 } | ConvertTo-Json
Invoke-RestMethod -Uri "$base/api/overlays/$id/opacity" -Method Post -Headers $headers -ContentType "application/json" -Body $body
```

Update several fields at once:

```powershell
$body = @{ x = 320; y = 260; scale = 1.1; opacity = 0.9; visible = $true } | ConvertTo-Json
Invoke-RestMethod -Uri "$base/api/overlays/$id/update" -Method Post -Headers $headers -ContentType "application/json" -Body $body
```

## Alias

```powershell
$body = @{ api_alias = "main_cat" } | ConvertTo-Json
Invoke-RestMethod -Uri "$base/api/overlays/$id/alias" -Method Post -Headers $headers -ContentType "application/json" -Body $body

Invoke-RestMethod -Uri "$base/api/overlays/resolve/main_cat" -Method Get
```

Aliases must be unique among active overlays. Duplicate aliases return `409 conflict`.

## Movement

```powershell
$body = @{
  enabled = $true
  velocity_x = 120
  velocity_y = 0
  bounce = $true
  gravity = 0
  friction = 0
} | ConvertTo-Json

Invoke-RestMethod -Uri "$base/api/overlays/$id/movement" -Method Post -Headers $headers -ContentType "application/json" -Body $body
```

## Actions

Supported action types match OpenAnima's overlay action system: `open_file`, `open_folder`, `open_url`, and `launch_app`. Short aliases such as `url`, `file`, `folder`, and `app` are accepted.

```powershell
$body = @{ type = "url"; target = "https://example.com" } | ConvertTo-Json
Invoke-RestMethod -Uri "$base/api/overlays/$id/action" -Method Post -Headers $headers -ContentType "application/json" -Body $body

Invoke-RestMethod -Uri "$base/api/overlays/$id/action/trigger" -Method Post -Headers $headers
```

## Animations

Named animations are available only for compatible spritesheet assets.

```powershell
Invoke-RestMethod -Uri "$base/api/overlays/$id/animations" -Method Get

$body = @{ animation_name = "Idle" } | ConvertTo-Json
Invoke-RestMethod -Uri "$base/api/overlays/$id/animation" -Method Post -Headers $headers -ContentType "application/json" -Body $body
```

## Composite UI Values

Composite UI / HUD assets can expose runtime values such as health or mana.

```powershell
Invoke-RestMethod -Uri "$base/api/overlays/$id/composite-values" -Method Get

$body = @{ health = 75; mana = 40; stamina = 90 } | ConvertTo-Json
Invoke-RestMethod -Uri "$base/api/overlays/$id/composite-values" -Method Post -Headers $headers -ContentType "application/json" -Body $body
```

Values may be sent as `0..1` or `0..100`.

## Scenes

```powershell
$body = @{ name = "coding_scene" } | ConvertTo-Json
Invoke-RestMethod -Uri "$base/api/scenes/save" -Method Post -Headers $headers -ContentType "application/json" -Body $body

Invoke-RestMethod -Uri "$base/api/scenes" -Method Get

$body = @{ name = "coding_scene"; replace_current = $true } | ConvertTo-Json
Invoke-RestMethod -Uri "$base/api/scenes/load" -Method Post -Headers $headers -ContentType "application/json" -Body $body

$body = @{ name = "coding_scene" } | ConvertTo-Json
Invoke-RestMethod -Uri "$base/api/scenes/export" -Method Post -Headers $headers -ContentType "application/json" -Body $body

$body = @{ path = "C:/path/to/scene.openanima-scene.json"; replace_current = $false } | ConvertTo-Json
Invoke-RestMethod -Uri "$base/api/scenes/import" -Method Post -Headers $headers -ContentType "application/json" -Body $body
```

When scenes are loaded additively, duplicate `persistent_id` values are replaced for copied overlays.

## Recovery

```powershell
Invoke-RestMethod -Uri "$base/api/recovery/show-all" -Method Post -Headers $headers
Invoke-RestMethod -Uri "$base/api/recovery/unlock-all" -Method Post -Headers $headers
Invoke-RestMethod -Uri "$base/api/recovery/disable-click-through-all" -Method Post -Headers $headers
Invoke-RestMethod -Uri "$base/api/recovery/center-all" -Method Post -Headers $headers
```

## Batch

```powershell
$body = @{
  operations = @(
    @{ action = "move"; id = $id; body = @{ x = 420; y = 260 } },
    @{ action = "opacity"; id = $id; body = @{ opacity = 0.75 } },
    @{ action = "recovery_center_all" }
  )
} | ConvertTo-Json -Depth 8

Invoke-RestMethod -Uri "$base/api/overlays/batch" -Method Post -Headers $headers -ContentType "application/json" -Body $body
```

## Recent Events

There is no WebSocket endpoint yet. Use the recent in-memory event buffer:

```powershell
Invoke-RestMethod -Uri "$base/api/events/recent" -Method Get
```

## Example Scripts

PowerShell:

```powershell
.\examples\local_api\powershell_demo.ps1 `
  -base "http://127.0.0.1:8765" `
  -token "YOUR_TOKEN" `
  -assetPath "D:/Openanima/OpenAnima/assets/bonzibuddy-ezgif.com-gif-to-webm-converter.gif"
```

Python standard library examples:

```bash
python examples/local_api/python_controller.py
python examples/local_api/scene_switcher.py
```

## Troubleshooting

**Unable to connect to the remote server**

OpenAnima may not be running, the Local API may be disabled, or the port may not be `8765`. Check the **Local API** page and copy the displayed Base URL.

**401 unauthorized**

The token is missing or wrong. Click **Copy API Token** on the Local API page and rebuild your `$headers` value.

**Port changed from 8765**

If `8765` is already in use, OpenAnima falls back to another local port. Use the Base URL shown in the UI.

**Asset import returns 501**

The selected asset needs the interactive Asset Setup workflow. Import/configure it from the OpenAnima UI first.

**overlay_not_found**

The overlay may not exist, may have been closed, or the script may be using an old `runtime_id`. Prefer `persistent_id` or set an `api_alias`.

## Limitations

* The Local API is experimental.
* There is no WebSocket endpoint yet; use `/api/events/recent`.
* Interactive asset setup is not automated through the API.
* The API is local-only and should not be exposed outside the machine.
