# Expose local PPD API over HTTPS via Cloudflare quick tunnel (free, no account).
# Usage:
#   1. Start API:  ppd serve --host 0.0.0.0 --port 8765
#   2. Run:        .\scripts\tunnel.ps1
#   3. Copy the https://....trycloudflare.com URL into the Flutter app API settings.

$ErrorActionPreference = "Stop"

$apiUrl = "http://127.0.0.1:8765"
$cloudflared = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
if (-not (Test-Path $cloudflared)) {
    $cloudflared = (Get-Command cloudflared -ErrorAction SilentlyContinue).Source
}
if (-not $cloudflared) {
    Write-Error "cloudflared not found. Install: winget install Cloudflare.cloudflared"
}

try {
    $health = Invoke-WebRequest -Uri "$apiUrl/health" -UseBasicParsing -TimeoutSec 3
    Write-Host "API healthy: $($health.Content)" -ForegroundColor Green
} catch {
    Write-Host "Start the API first:" -ForegroundColor Yellow
    Write-Host "  ppd serve --host 0.0.0.0 --port 8765"
    exit 1
}

Write-Host ""
Write-Host "Starting Cloudflare quick tunnel -> $apiUrl" -ForegroundColor Cyan
Write-Host "Copy the https://....trycloudflare.com URL into the Flutter app (API settings)." -ForegroundColor Cyan
Write-Host "Keep this window open. Ctrl+C stops the tunnel." -ForegroundColor DarkGray
Write-Host ""

& $cloudflared tunnel --url $apiUrl
