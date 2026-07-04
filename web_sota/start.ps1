$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSCommandPath

# Clear port zombies
Get-NetTCPConnection -LocalPort 11075 -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

npm run dev
