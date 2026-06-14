@echo off
cd /d "%~dp0"
REM Prefer source (latest fixes). Falls back to bundled exe.
python -m ppd.gui_web
if not errorlevel 1 exit /b 0
if exist "dist-win\PPD-Resume\PPD-Resume.exe" (
    start "" "dist-win\PPD-Resume\PPD-Resume.exe"
) else if exist "dist\PPD-Resume\PPD-Resume.exe" (
    start "" "dist\PPD-Resume\PPD-Resume.exe"
) else (
    echo Python not found and no exe built. Run: pip install -e .
    pause
)
