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
    else { throw "Build failed — PPD-Resume.exe not found." }
}

$tools = Join-Path $dist "tools"
New-Item -ItemType Directory -Force -Path $tools | Out-Null

$typstCmd = Get-Command typst -ErrorAction SilentlyContinue
if ($null -ne $typstCmd) {
    Copy-Item $typstCmd.Source (Join-Path $tools "typst.exe") -Force
    Write-Host "Bundled typst.exe from PATH" -ForegroundColor Green
}
else {
    Write-Host "Typst not on PATH - downloading portable typst..." -ForegroundColor Yellow
    $zipUrl = "https://github.com/typst/typst/releases/download/v0.14.2/typst-x86_64-pc-windows-msvc.zip"
    $zipPath = Join-Path $env:TEMP "typst.zip"
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing
    $extractDir = Join-Path $env:TEMP "typst-extract"
    Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force
    $typstExe = Get-ChildItem -Path $extractDir -Recurse -Filter "typst.exe" | Select-Object -First 1
    if ($null -ne $typstExe) {
        Copy-Item $typstExe.FullName (Join-Path $tools "typst.exe") -Force
        Write-Host "Bundled typst.exe from GitHub release" -ForegroundColor Green
    }
    else {
        Write-Host "Could not bundle Typst - install manually: winget install Typst.Typst" -ForegroundColor Red
    }
}

New-Item -ItemType Directory -Force -Path (Join-Path $dist "data\source") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $dist "output") | Out-Null

Write-Host ""
Write-Host "Done! Run:" -ForegroundColor Green
Write-Host "  $dist\PPD-Resume.exe" -ForegroundColor White
Write-Host ""
Write-Host "Copy the entire dist\PPD-Resume folder anywhere and double-click PPD-Resume.exe" -ForegroundColor Cyan
