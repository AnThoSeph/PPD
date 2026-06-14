# Bundle Typst + Tesseract into a PPD dist folder (shared by local builds and CI)

param(
    [Parameter(Mandatory = $true)]
    [string]$DistDir,

    [string]$TypstVersion = "0.14.2"
)

$ErrorActionPreference = "Stop"
$tools = Join-Path $DistDir "tools"
New-Item -ItemType Directory -Force -Path $tools, (Join-Path $DistDir "data/source"), (Join-Path $DistDir "output") | Out-Null

# --- Typst ---
$typstCmd = Get-Command typst -ErrorAction SilentlyContinue
if ($null -ne $typstCmd) {
    Copy-Item $typstCmd.Source (Join-Path $tools "typst.exe") -Force
    Write-Host "Bundled typst.exe from PATH"
}
else {
    $zipUrl = "https://github.com/typst/typst/releases/download/v$TypstVersion/typst-x86_64-pc-windows-msvc.zip"
    $zipPath = Join-Path $env:TEMP "typst.zip"
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing
    $extractDir = Join-Path $env:TEMP "typst-extract"
    if (Test-Path $extractDir) { Remove-Item $extractDir -Recurse -Force }
    Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force
    $typstExe = Get-ChildItem -Path $extractDir -Recurse -Filter "typst.exe" | Select-Object -First 1
    if ($null -eq $typstExe) { throw "Could not find typst.exe in download" }
    Copy-Item $typstExe.FullName (Join-Path $tools "typst.exe") -Force
    Write-Host "Bundled typst.exe from GitHub"
}

# --- Tesseract (for image OCR) ---
function Copy-TesseractFrom($src) {
    $exe = Join-Path $src "tesseract.exe"
    if (-not (Test-Path $exe)) { return $false }
    # Copy exe + DLLs (tesseract depends on leptonica etc.)
    Get-ChildItem -Path $src -File | ForEach-Object {
        Copy-Item $_.FullName (Join-Path $tools $_.Name) -Force
    }
    $tessdataSrc = Join-Path $src "tessdata"
    $tessdataDst = Join-Path $tools "tessdata"
    if (Test-Path $tessdataSrc) {
        if (Test-Path $tessdataDst) { Remove-Item $tessdataDst -Recurse -Force }
        Copy-Item $tessdataSrc $tessdataDst -Recurse -Force
    }
    Write-Host "Bundled Tesseract from $src"
    return $true
}

$bundled = $false
foreach ($dir in @(
    "C:\Program Files\Tesseract-OCR",
    "C:\Program Files (x86)\Tesseract-OCR",
    "$env:LOCALAPPDATA\Programs\Tesseract-OCR"
)) {
    if (Copy-TesseractFrom $dir) { $bundled = $true; break }
}

if (-not $bundled) {
    Write-Host "Tesseract not found - installing via winget for bundling..."
    winget install --id UB-Mannheim.TesseractOCR -e --accept-source-agreements --accept-package-agreements 2>$null
    foreach ($dir in @(
        "C:\Program Files\Tesseract-OCR",
        "C:\Program Files (x86)\Tesseract-OCR"
    )) {
        if (Copy-TesseractFrom $dir) { $bundled = $true; break }
    }
}

if (-not $bundled) {
    Write-Host "WARNING: Could not bundle Tesseract - image uploads will require manual install." -ForegroundColor Yellow
}

Write-Host "Tools ready in $tools"
