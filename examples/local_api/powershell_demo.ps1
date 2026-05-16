param(
  [string]$base = "http://127.0.0.1:8765",
  [string]$token = "YOUR_TOKEN",
  [string]$assetPath = ""
)

$ErrorActionPreference = "Stop"
$headers = @{ "X-OpenAnima-Token" = $token }

function Step($name) {
  Write-Host ""
  Write-Host "== $name =="
}

function PostJson($path, $body = $null) {
  $uri = "$base$path"
  if ($body -eq $null) {
    return Invoke-RestMethod -Uri $uri -Method Post -Headers $headers
  }
  $json = $body | ConvertTo-Json -Depth 8
  return Invoke-RestMethod -Uri $uri -Method Post -Headers $headers -ContentType "application/json" -Body $json
}

Step "Status"
Invoke-RestMethod -Uri "$base/api/status" -Method Get | Format-List

Step "Assets"
@(Invoke-RestMethod -Uri "$base/api/assets" -Method Get) | Select-Object -First 10 | Format-Table name, type, pack

Step "Overlays"
$overlays = @(Invoke-RestMethod -Uri "$base/api/overlays/all" -Method Get)
$overlays | Format-Table id, runtime_id, persistent_id, api_alias, asset_name

$created = $null
if ($assetPath -and (Test-Path $assetPath)) {
  Step "Spawn Overlay"
  $created = PostJson "/api/overlays/spawn" @{
    asset_path = $assetPath
    x = 200
    y = 200
    scale = 1.0
    opacity = 1.0
  }
  $created | Format-List
} elseif ($assetPath) {
  Write-Warning "assetPath does not exist: $assetPath"
}

$overlays = @(Invoke-RestMethod -Uri "$base/api/overlays/all" -Method Get)
if ($created) {
  $id = $created.persistent_id
} elseif ($overlays.Count -gt 0) {
  $id = $overlays[0].persistent_id
} else {
  Write-Host "No overlay available. Provide -assetPath to spawn one."
  exit 0
}

Step "Resolve Overlay"
Invoke-RestMethod -Uri "$base/api/overlays/resolve/$id" -Method Get | Format-List

Step "Set Alias"
PostJson "/api/overlays/$id/alias" @{ api_alias = "demo_overlay" } | Format-List
$id = "demo_overlay"

Step "Move / Scale / Opacity / Visibility"
PostJson "/api/overlays/$id/move" @{ x = 320; y = 260 } | Out-Null
PostJson "/api/overlays/$id/scale" @{ scale = 1.2 } | Out-Null
PostJson "/api/overlays/$id/opacity" @{ opacity = 0.8 } | Out-Null
PostJson "/api/overlays/$id/visibility" @{ visible = $true } | Format-List

Step "Save Scene"
PostJson "/api/scenes/save" @{ name = "demo_scene" } | Format-List

Step "Load Scene Additively"
PostJson "/api/scenes/load" @{ name = "demo_scene"; replace_current = $false } | Format-List

Step "Recent Events"
Invoke-RestMethod -Uri "$base/api/events/recent" -Method Get | Select-Object -Last 10 | Format-Table type, timestamp

if ($created) {
  Step "Close Created Overlay"
  PostJson "/api/overlays/$($created.persistent_id)/close" | Format-List
}
