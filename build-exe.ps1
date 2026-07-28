# Build PPD-Resume.exe - run from project root in PowerShell

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "Installing build dependencies..." -ForegroundColor Cyan
python -m pip install -e . -q
python -m pip install pyinstaller -q

Write-Host "Building executable..." -ForegroundColor Cyan

# Stop a running copy so PyInstaller can replace dist\PPD-Resume
Get-Process -Name "PPD-Resume" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

$dist = Join-Path $PSScriptRoot "dist\PPD-Resume"
python -m PyInstaller ppd.spec --noconfirm --clean
if ($LASTEXITCODE -ne 0 -or -not (Test-Path (Join-Path $dist "PPD-Resume.exe"))) {
    Write-Host "Build to dist failed (folder may be locked). Trying dist-win..." -ForegroundColor Yellow
    $dist = Join-Path $PSScriptRoot "dist-win\PPD-Resume"
    python -m PyInstaller ppd.spec --noconfirm --distpath (Join-Path $PSScriptRoot "dist-win") --workpath (Join-Path $PSScriptRoot "build")
}

if (-not (Test-Path (Join-Path $dist "PPD-Resume.exe"))) {
    $alt = Join-Path $PSScriptRoot "dist-win\PPD-Resume"
    if (Test-Path (Join-Path $alt "PPD-Resume.exe")) { $dist = $alt }
    else { throw "Build failed - PPD-Resume.exe not found." }
}

$tools = Join-Path $dist "tools"
New-Item -ItemType Directory -Force -Path $tools | Out-Null

& (Join-Path $PSScriptRoot "scripts\bundle-tools-windows.ps1") -DistDir $dist

Write-Host ""
Write-Host "Done! Run:" -ForegroundColor Green
Write-Host "  $dist\PPD-Resume.exe" -ForegroundColor White
Write-Host ""
Write-Host "Copy the entire dist\PPD-Resume folder anywhere and double-click PPD-Resume.exe" -ForegroundColor Cyan
