"""Import resume content from images via OCR."""

from __future__ import annotations

from pathlib import Path

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


def extract_text_lines(image_path: Path) -> list[str]:
    """Run OCR on an image and return non-empty text lines."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "Image OCR requires: pip install pillow pytesseract\n"
            "Also install Tesseract: winget install UB-Mannheim.TesseractOCR"
        ) from exc

    try:
        pytesseract.get_tesseract_version()
    except Exception as exc:
        raise RuntimeError(
            "Tesseract OCR is not installed or not on PATH.\n"
            "Install with: winget install UB-Mannheim.TesseractOCR"
        ) from exc

    image = Image.open(image_path)
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    text = pytesseract.image_to_string(image)
    return [line.strip() for line in text.splitlines() if line.strip()]
