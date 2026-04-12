# Runs migrations/0*.sql in order via docker-compose postgres (Windows; no sh/bash required).
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $repoRoot

Get-ChildItem -LiteralPath (Join-Path $repoRoot 'migrations') -Filter '0*.sql' |
    Sort-Object -Property Name |
    ForEach-Object {
        Write-Host "=== $($_.FullName) ==="
        $p = $_.FullName
        cmd /c "docker-compose exec -T postgres psql -U solvia -d solvia -v ON_ERROR_STOP=1 < `"$p`""
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
