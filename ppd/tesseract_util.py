"""Locate Tesseract OCR for image resume imports."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from ppd.paths import app_root

_WINDOWS_INSTALL_DIRS = (
    Path(r"C:\Program Files\Tesseract-OCR"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR"),
    Path.home() / "AppData" / "Local" / "Programs" / "Tesseract-OCR",
)


def _has_eng_tessdata(tessdata_dir: Path) -> bool:
    return (tessdata_dir / "eng.traineddata").exists()


def _tessdata_for_exe(exe: Path) -> Path | None:
    for candidate in (
        exe.parent / "tessdata",
        exe.parent.parent / "tessdata",
        exe.parent / "share" / "tessdata",
    ):
        if _has_eng_tessdata(candidate):
            return candidate
    return None


def find_tesseract() -> Path:
    """Return path to tesseract executable."""
    root = app_root()
    candidates: list[Path] = [
        root / "tools" / "tesseract.exe",
        root / "tools" / "tesseract",
    ]
    if sys.platform == "win32":
        candidates.extend(d / "tesseract.exe" for d in _WINDOWS_INSTALL_DIRS)

    which = shutil.which("tesseract")
    if which:
        candidates.append(Path(which))

    for path in candidates:
        if path.is_file():
            return path

    raise RuntimeError(
        "Tesseract OCR is required for image uploads (PNG, JPG, etc.).\n\n"
        "Install it, then restart PPD:\n"
        "  winget install UB-Mannheim.TesseractOCR\n\n"
        "PDF uploads do not need Tesseract."
    )


def configure_tesseract() -> Path:
    """Point pytesseract at a working binary and tessdata. Returns exe path."""
    import pytesseract

    exe = find_tesseract()
    pytesseract.pytesseract.tesseract_cmd = str(exe)

    tessdata = _tessdata_for_exe(exe)
    if tessdata is not None:
        # Tesseract expects the parent of the tessdata folder.
        os.environ["TESSDATA_PREFIX"] = str(tessdata.parent)

    try:
        pytesseract.get_tesseract_version()
    except Exception as exc:
        raise RuntimeError(
            f"Tesseract was found at {exe} but failed to run.\n"
            "Reinstall with: winget install UB-Mannheim.TesseractOCR"
        ) from exc

    return exe
