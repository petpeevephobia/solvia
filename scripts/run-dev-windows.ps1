# Start API (minimized console) then web dev server in foreground — used by `make dev` on Windows (no bash &/sleep).
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$apiDir = Join-Path $root 'api'
$webDir = Join-Path $root 'web'

Start-Process -FilePath 'go' -ArgumentList @('run', './cmd/api') -WorkingDirectory $apiDir -WindowStyle Minimized
Start-Sleep -Seconds 3
Set-Location -LiteralPath $webDir
npm run dev
