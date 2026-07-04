$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Dist = Join-Path $Root "dist"
New-Item -ItemType Directory -Force -Path $Dist | Out-Null

Write-Host "=== Packing sysinternals-mcp ===" -ForegroundColor Cyan
uv run python -m mcpb pack "$Root" "$Dist\sysinternals-mcp-v0.1.0.mcpb"
Write-Host "Created: $Dist\sysinternals-mcp-v0.1.0.mcpb" -ForegroundColor Green
