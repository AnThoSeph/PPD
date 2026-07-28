"""Import resume content from images via OCR."""

from __future__ import annotations

from pathlib import Path

from ppd.tesseract_util import configure_tesseract

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


def extract_text_lines(image_path: Path) -> list[str]:
    """Run OCR on an image and return non-empty text lines."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "Image OCR requires pillow and pytesseract.\n"
            "Reinstall PPD or run: pip install pillow pytesseract"
        ) from exc

    configure_tesseract()

    image = Image.open(image_path)
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    text = pytesseract.image_to_string(image)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(
            "OCR found no text in this image.\n"
            "Use a clear, high-resolution photo or scan — or upload a PDF instead."
        )
    return lines
