@echo off
cd /d "%~dp0"
if exist "dist-win\PPD-Resume\PPD-Resume.exe" (
  start "" "dist-win\PPD-Resume\PPD-Resume.exe"
) else if exist "dist\PPD-Resume\PPD-Resume.exe" (
  start "" "dist\PPD-Resume\PPD-Resume.exe"
) else (
  echo PPD-Resume.exe not found. Run build-exe.bat first.
  pause
)
